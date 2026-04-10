"""
主控制节点
整合所有模块，提供统一接口
"""

import threading
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .core import (
    EventBus, Event, EventType,
    StateMachine, RobotState,
    RobotStatusManager, RobotStatus, Position, TargetInfo
)
from .sensors import (
    SensorManager, DepthCameraSensor, LidarSensor, GPSSensor, IMUSensor,
    DepthImageData, LidarScanData
)
from .motion import (
    MotionManager, MotionConfig, Pose, VelocityCommand
)
from .scheduler import (
    TaskScheduler, TaskPriority, MissionPlanner
)

logger = logging.getLogger("RobotController")


class FarmRobotController:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        self.event_bus = EventBus()
        
        self.state_machine = StateMachine(self.event_bus)
        self.status_manager = RobotStatusManager(self.event_bus)
        
        motion_config = MotionConfig(
            max_linear_speed=self.config.get("max_linear_speed", 2.0),
            max_angular_speed=self.config.get("max_angular_speed", 2.0),
            wheel_base=self.config.get("wheel_base", 0.5),
            wheel_radius=self.config.get("wheel_radius", 0.15)
        )
        self.motion_manager = MotionManager(self.event_bus, motion_config)
        
        self.sensor_manager = SensorManager(self.event_bus)
        self._setup_sensors()
        
        self.task_scheduler = TaskScheduler(self.event_bus)
        self.task_scheduler.set_robot_controller(self)
        self.mission_planner = MissionPlanner(self.task_scheduler, self.event_bus)
        
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        self._detected_targets: List[TargetInfo] = []
        self._lock = threading.Lock()
    
    def _setup_sensors(self):
        depth_camera = DepthCameraSensor(
            self.event_bus,
            model_path=self.config.get("model_path", "best.pt")
        )
        lidar = LidarSensor(
            self.event_bus,
            num_readings=self.config.get("lidar_readings", 360),
            max_range=self.config.get("lidar_max_range", 30.0)
        )
        gps = GPSSensor(self.event_bus)
        imu = IMUSensor(self.event_bus)
        
        self.sensor_manager.register_sensor(depth_camera)
        self.sensor_manager.register_sensor(lidar)
        self.sensor_manager.register_sensor(gps)
        self.sensor_manager.register_sensor(imu)
    
    def initialize(self) -> bool:
        logger.info("Initializing Farm Robot Controller...")
        
        self.state_machine.transition_to(RobotState.INITIALIZING)
        self.status_manager.update_status(state=RobotState.INITIALIZING)
        
        try:
            self.sensor_manager.start_all()
            time.sleep(1.0)
            
            self.motion_manager.start()
            self.task_scheduler.start()
            
            self.state_machine.transition_to(RobotState.READY)
            self.status_manager.update_status(state=RobotState.READY)
            
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            
            logger.info("Farm Robot Controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self.state_machine.transition_to(RobotState.ERROR)
            self.status_manager.update_status(
                state=RobotState.ERROR,
                error_message=str(e)
            )
            return False
    
    def shutdown(self):
        logger.info("Shutting down Farm Robot Controller...")
        
        self._running = False
        
        self.task_scheduler.stop()
        self.motion_manager.stop()
        self.sensor_manager.stop_all()
        
        self.state_machine.transition_to(RobotState.SHUTDOWN)
        self.status_manager.update_status(state=RobotState.SHUTDOWN)
        
        logger.info("Farm Robot Controller shutdown complete")
    
    def emergency_stop(self):
        logger.warning("EMERGENCY STOP triggered")
        self.motion_manager.emergency_stop()
        self.state_machine.transition_to(RobotState.EMERGENCY_STOP)
        self.status_manager.update_status(state=RobotState.EMERGENCY_STOP)
    
    def resume_from_emergency(self):
        if self.state_machine.current_state == RobotState.EMERGENCY_STOP:
            self.state_machine.transition_to(RobotState.READY)
            self.status_manager.update_status(state=RobotState.READY)
    
    def navigate_to(self, x: float, y: float) -> bool:
        if self.state_machine.current_state not in [
            RobotState.READY, RobotState.NAVIGATING
        ]:
            logger.warning(f"Cannot navigate in state: {self.state_machine.current_state}")
            return False
        
        self.state_machine.transition_to(RobotState.NAVIGATING)
        self.status_manager.update_status(state=RobotState.NAVIGATING)
        
        target_pose = Pose(x=x, y=y)
        self.motion_manager.navigation_controller.set_target(target_pose)
        
        return True
    
    def scan_for_targets(self) -> List[Dict[str, Any]]:
        if self.state_machine.current_state not in [
            RobotState.READY, RobotState.SCANNING, RobotState.NAVIGATING
        ]:
            return []
        
        self.state_machine.transition_to(RobotState.SCANNING)
        self.status_manager.update_status(state=RobotState.SCANNING)
        
        depth_camera = self.sensor_manager.get_sensor("DepthCamera")
        if not depth_camera:
            return []
        
        data = depth_camera.get_latest_data(timeout=1.0)
        if not data or not isinstance(data, DepthImageData):
            return []
        
        detections = depth_camera.detect_objects(data)
        
        with self._lock:
            self._detected_targets = []
            for det in detections:
                target = TargetInfo(
                    position=Position(x=det.get("depth", 0), y=det.get("center", (0, 0))[0]),
                    confidence=det.get("confidence", 0),
                    target_type=det.get("class", "unknown"),
                    bounding_box=det.get("bbox")
                )
                self._detected_targets.append(target)
        
        self.state_machine.transition_to(RobotState.READY)
        self.status_manager.update_status(state=RobotState.READY)
        
        return [
            {
                "position": {"x": t.position.x, "y": t.position.y},
                "confidence": t.confidence,
                "type": t.target_type,
                "bbox": t.bounding_box
            }
            for t in self._detected_targets
        ]
    
    def identify_target(self, target: Dict[str, Any]) -> Dict[str, Any]:
        self.state_machine.transition_to(RobotState.IDENTIFYING)
        self.status_manager.update_status(state=RobotState.IDENTIFYING)
        
        result = {
            "target_id": target.get("id", "unknown"),
            "confirmed": target.get("confidence", 0) > 0.7,
            "type": target.get("type", "unknown"),
            "action_recommended": "eradicate" if target.get("confidence", 0) > 0.7 else "ignore"
        }
        
        self.state_machine.transition_to(RobotState.READY)
        self.status_manager.update_status(state=RobotState.READY)
        
        return result
    
    def fire_laser(self, duration: float = 0.5) -> bool:
        if self.state_machine.current_state not in [
            RobotState.READY, RobotState.EXECUTING
        ]:
            logger.warning(f"Cannot fire laser in state: {self.state_machine.current_state}")
            return False
        
        self.state_machine.transition_to(RobotState.EXECUTING)
        self.status_manager.update_status(state=RobotState.EXECUTING)
        
        success = self.motion_manager.laser_controller.fire(duration)
        
        self.state_machine.transition_to(RobotState.READY)
        self.status_manager.update_status(state=RobotState.READY)
        
        return success
    
    def execute_patrol(self, waypoints: List[Dict[str, float]]) -> str:
        return self.mission_planner.create_patrol_mission(waypoints)
    
    def execute_scan(self, duration: int = 30) -> str:
        return self.mission_planner.create_scan_mission(duration)
    
    def execute_eradication(self, targets: List[Dict[str, Any]]) -> str:
        return self.mission_planner.create_eradication_mission(targets)
    
    def get_battery_level(self) -> float:
        return self.status_manager.status.battery_level
    
    def get_robot_status(self) -> Dict[str, Any]:
        return {
            "state": self.state_machine.current_state.value,
            "position": self.status_manager.status.position.to_dict(),
            "battery_level": self.status_manager.status.battery_level,
            "temperature": self.status_manager.status.temperature,
            "error_code": self.status_manager.status.error_code
        }
    
    def get_motion_status(self) -> Dict[str, Any]:
        return self.motion_manager.get_status()
    
    def get_sensor_data(self) -> Dict[str, Any]:
        data = {}
        
        depth_camera = self.sensor_manager.get_sensor("DepthCamera")
        if depth_camera:
            latest = depth_camera.get_latest_data()
            if latest:
                data["depth_camera"] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "resolution": f"{latest.width}x{latest.height}"
                }
        
        lidar = self.sensor_manager.get_sensor("Lidar")
        if lidar:
            latest = lidar.get_latest_data()
            if latest and latest.ranges is not None:
                data["lidar"] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "range_min": latest.min_range,
                    "range_max": latest.max_range,
                    "readings": len(latest.ranges)
                }
        
        gps = self.sensor_manager.get_sensor("GPS")
        if gps:
            latest = gps.get_latest_data()
            if latest:
                data["gps"] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "latitude": latest.latitude,
                    "longitude": latest.longitude,
                    "altitude": latest.altitude,
                    "fix_quality": latest.fix_quality
                }
        
        imu = self.sensor_manager.get_sensor("IMU")
        if imu:
            latest = imu.get_latest_data()
            if latest:
                data["imu"] = {
                    "timestamp": latest.timestamp.isoformat(),
                    "orientation": latest.orientation,
                    "temperature": latest.temperature
                }
        
        return data
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        return self.task_scheduler.get_all_tasks()
    
    def _monitor_loop(self):
        while self._running:
            try:
                self._update_battery_simulation()
                self._check_safety_conditions()
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def _update_battery_simulation(self):
        current = self.status_manager.status.battery_level
        if current > 0:
            new_level = max(0, current - 0.01)
            self.status_manager.update_status(battery_level=new_level)
    
    def _check_safety_conditions(self):
        lidar = self.sensor_manager.get_sensor("Lidar")
        if lidar:
            latest = lidar.get_latest_data(timeout=0.5)
            if latest and latest.ranges is not None:
                min_distance = float(min(latest.ranges))
                if min_distance < 0.3:
                    logger.warning(f"Obstacle detected at {min_distance}m - Emergency stop")
                    self.emergency_stop()
        
        temp = self.status_manager.status.temperature
        if temp > 60:
            logger.warning(f"Overheating: {temp}°C - Emergency stop")
            self.emergency_stop()


class RobotAPI:
    def __init__(self, controller: FarmRobotController):
        self.controller = controller
    
    def start(self) -> Dict[str, Any]:
        success = self.controller.initialize()
        return {"success": success, "status": self.controller.get_robot_status()}
    
    def stop(self) -> Dict[str, Any]:
        self.controller.shutdown()
        return {"success": True, "message": "Robot stopped"}
    
    def status(self) -> Dict[str, Any]:
        return self.controller.get_robot_status()
    
    def motion_status(self) -> Dict[str, Any]:
        return self.controller.get_motion_status()
    
    def sensor_data(self) -> Dict[str, Any]:
        return self.controller.get_sensor_data()
    
    def navigate(self, x: float, y: float) -> Dict[str, Any]:
        success = self.controller.navigate_to(x, y)
        return {"success": success, "target": {"x": x, "y": y}}
    
    def scan(self, duration: int = 30) -> Dict[str, Any]:
        task_id = self.controller.execute_scan(duration)
        return {"success": True, "task_id": task_id}
    
    def targets(self) -> Dict[str, Any]:
        return {"targets": self.controller.scan_for_targets()}
    
    def eradicate(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        task_id = self.controller.execute_eradication(targets)
        return {"success": True, "task_id": task_id}
    
    def patrol(self, waypoints: List[Dict[str, float]]) -> Dict[str, Any]:
        task_id = self.controller.execute_patrol(waypoints)
        return {"success": True, "task_id": task_id}
    
    def tasks(self) -> Dict[str, Any]:
        return {"tasks": self.controller.get_tasks()}
    
    def emergency(self) -> Dict[str, Any]:
        self.controller.emergency_stop()
        return {"success": True, "message": "Emergency stop triggered"}
    
    def resume(self) -> Dict[str, Any]:
        self.controller.resume_from_emergency()
        return {"success": True, "message": "Resumed from emergency"}
