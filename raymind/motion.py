"""
运动控制模块
支持差分驱动、麦轮、全向移动等多种底盘控制
"""

import threading
import time
import math
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger("MotionControl")


class MotionMode(Enum):
    STOP = "stop"
    FORWARD = "forward"
    BACKWARD = "backward"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    STRAFE_LEFT = "strafe_left"
    STRAFE_RIGHT = "strafe_right"
    ARC = "arc"
    POSITION_CONTROL = "position_control"


@dataclass
class MotorCommand:
    left_speed: float = 0.0
    right_speed: float = 0.0
    left_direction: int = 1
    right_direction: int = 1
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VelocityCommand:
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Pose:
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "theta": self.theta}
    
    def distance_to(self, other: 'Pose') -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)


@dataclass
class MotionStatus:
    mode: MotionMode = MotionMode.STOP
    current_velocity: VelocityCommand = field(default_factory=VelocityCommand)
    current_pose: Pose = field(default_factory=Pose)
    target_pose: Optional[Pose] = None
    left_motor_speed: float = 0.0
    right_motor_speed: float = 0.0
    battery_voltage: float = 24.0
    motor_temperature: float = 25.0
    encoder_left: int = 0
    encoder_right: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MotionConfig:
    max_linear_speed: float = 2.0
    max_angular_speed: float = 2.0
    max_acceleration: float = 1.0
    wheel_base: float = 0.5
    wheel_radius: float = 0.15
    encoder_ppr: int = 4096
    pid_kp: float = 1.0
    pid_ki: float = 0.1
    pid_kd: float = 0.05


class MotorController:
    def __init__(self, config: MotionConfig, event_bus):
        self.config = config
        self.event_bus = event_bus
        self._running = False
        self._control_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._target_velocity = VelocityCommand()
        self._current_pose = Pose()
        self._velocity_history: List[VelocityCommand] = []
        
        self._pid_integral_left = 0.0
        self._pid_integral_right = 0.0
        self._last_error_left = 0.0
        self._last_error_right = 0.0
        
        self._left_motor_power = 0.0
        self._right_motor_power = 0.0
    
    def start(self):
        if not self._running:
            self._running = True
            self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self._control_thread.start()
            logger.info("Motor controller started")
    
    def stop(self):
        self._running = False
        if self._control_thread:
            self._control_thread.join(timeout=2.0)
        self._left_motor_power = 0.0
        self._right_motor_power = 0.0
        logger.info("Motor controller stopped")
    
    def set_velocity(self, cmd: VelocityCommand):
        with self._lock:
            cmd.linear_x = max(-self.config.max_linear_speed, 
                             min(self.config.max_linear_speed, cmd.linear_x))
            cmd.linear_y = max(-self.config.max_linear_speed,
                             min(self.config.max_linear_speed, cmd.linear_y))
            cmd.angular_z = max(-self.config.max_angular_speed,
                               min(self.config.max_angular_speed, cmd.angular_z))
            self._target_velocity = cmd
    
    def stop_motors(self):
        with self._lock:
            self._target_velocity = VelocityCommand()
    
    def get_status(self) -> MotionStatus:
        with self._lock:
            return MotionStatus(
                current_velocity=VelocityCommand(
                    linear_x=self._target_velocity.linear_x,
                    linear_y=self._target_velocity.linear_y,
                    angular_z=self._target_velocity.angular_z
                ),
                current_pose=Pose(**self._current_pose.to_dict()),
                left_motor_speed=self._left_motor_power,
                right_motor_speed=self._right_motor_power
            )
    
    def _control_loop(self):
        dt = 0.02
        while self._running:
            try:
                with self._lock:
                    target_v = self._target_velocity
                    current_pose = self._current_pose
                
                left_speed, right_speed = self._differential_drive_ik(
                    target_v.linear_x, target_v.angular_z
                )
                
                left_power = self._pid_control(left_speed, self._left_motor_power, 
                                               self._pid_integral_left, self._last_error_left)
                right_power = self._pid_control(right_speed, self._right_motor_power,
                                                self._pid_integral_right, self._last_error_right)
                
                with self._lock:
                    self._left_motor_power = left_power
                    self._right_motor_power = right_power
                
                self._update_pose(target_v, dt)
                
                time.sleep(dt)
            except Exception as e:
                logger.error(f"Motor control error: {e}")
                time.sleep(0.1)
    
    def _differential_drive_ik(self, linear_x: float, angular_z: float) -> Tuple[float, float]:
        wheel_base = self.config.wheel_base
        v_left = linear_x - (angular_z * wheel_base / 2)
        v_right = linear_x + (angular_z * wheel_base / 2)
        return v_left, v_right
    
    def _pid_control(self, target: float, current: float, 
                     integral: float, last_error: float) -> float:
        error = target - current
        integral = max(-10, min(10, integral + error * 0.02))
        derivative = (error - last_error) / 0.02
        
        output = (self.config.pid_kp * error + 
                 self.config.pid_ki * integral + 
                 self.config.pid_kd * derivative)
        
        return max(-1.0, min(1.0, output))
    
    def _update_pose(self, velocity: VelocityCommand, dt: float):
        dx = velocity.linear_x * math.cos(self._current_pose.theta) * dt
        dy = velocity.linear_x * math.sin(self._current_pose.theta) * dt
        dtheta = velocity.angular_z * dt
        
        self._current_pose.x += dx
        self._current_pose.y += dy
        self._current_pose.theta += dtheta
        
        self._current_pose.theta = math.atan2(math.sin(self._current_pose.theta),
                                              math.cos(self._current_pose.theta))
    
    def reset_pose(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0):
        with self._lock:
            self._current_pose = Pose(x=x, y=y, theta=theta)


class NavigationController:
    def __init__(self, motor_controller: MotorController, event_bus):
        self.motor_controller = motor_controller
        self.event_bus = event_bus
        self._running = False
        self._nav_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._waypoints: List[Pose] = []
        self._current_waypoint_index = 0
        self._target_pose: Optional[Pose] = None
        
        self._position_tolerance = 0.1
        self._angle_tolerance = 0.05
        
        self._max_linear_speed = 1.0
        self._max_angular_speed = 1.5
    
    def start(self):
        if not self._running:
            self._running = True
            self._nav_thread = threading.Thread(target=self._navigation_loop, daemon=True)
            self._nav_thread.start()
            logger.info("Navigation controller started")
    
    def stop(self):
        self._running = False
        if self._nav_thread:
            self._nav_thread.join(timeout=2.0)
        self.motor_controller.stop_motors()
        logger.info("Navigation controller stopped")
    
    def set_target(self, pose: Pose):
        with self._lock:
            self._target_pose = pose
        logger.info(f"Target set: {pose.x}, {pose.y}, {pose.theta}")
    
    def set_waypoints(self, waypoints: List[Pose]):
        with self._lock:
            self._waypoints = waypoints
            self._current_waypoint_index = 0
        logger.info(f"Waypoints set: {len(waypoints)} points")
    
    def clear_waypoints(self):
        with self._lock:
            self._waypoints = []
            self._current_waypoint_index = 0
    
    def _navigation_loop(self):
        while self._running:
            try:
                with self._lock:
                    target = self._target_pose
                    waypoints = self._waypoints
                    waypoint_index = self._current_waypoint_index
                
                if waypoints and waypoint_index < len(waypoints):
                    target = waypoints[waypoint_index]
                
                if target:
                    cmd = self._compute_velocity_command(target)
                    self.motor_controller.set_velocity(cmd)
                    
                    current_pose = self.motor_controller.get_status().current_pose
                    
                    if target.distance_to(current_pose) < self._position_tolerance:
                        if waypoints and waypoint_index < len(waypoints):
                            with self._lock:
                                self._current_waypoint_index += 1
                            logger.info(f"Waypoint {waypoint_index} reached")
                        elif self._target_pose:
                            logger.info("Target reached")
                            with self._lock:
                                self._target_pose = None
                
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Navigation error: {e}")
                time.sleep(0.1)
    
    def _compute_velocity_command(self, target: Pose) -> VelocityCommand:
        current_pose = self.motor_controller.get_status().current_pose
        
        dx = target.x - current_pose.x
        dy = target.y - current_pose.y
        distance = math.sqrt(dx**2 + dy**2)
        
        target_angle = math.atan2(dy, dx)
        angle_diff = target_angle - current_pose.theta
        angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
        
        linear_speed = min(self._max_linear_speed, distance * 2.0)
        
        if distance < self._position_tolerance:
            if abs(angle_diff) < self._angle_tolerance:
                linear_speed = 0.0
                angular_speed = 0.0
            else:
                linear_speed = 0.0
                angular_speed = self._max_angular_speed if angle_diff > 0 else -self._max_angular_speed
        else:
            angular_speed = self._max_angular_speed * angle_diff
            angular_speed = max(-self._max_angular_speed, min(self._max_angular_speed, angular_speed))
        
        return VelocityCommand(linear_x=linear_speed, angular_z=angular_speed)


class LaserController:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._running = False
        self._laser_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._fire_power = 0.0
        self._fire_duration = 0.5
        self._is_firing = False
        self._fire_count = 0
    
    def start(self):
        if not self._running:
            self._running = True
            self._laser_thread = threading.Thread(target=self._laser_loop, daemon=True)
            self._laser_thread.start()
            logger.info("Laser controller started")
    
    def stop(self):
        self._running = False
        if self._laser_thread:
            self._laser_thread.join(timeout=2.0)
        logger.info("Laser controller stopped")
    
    def fire(self, duration: float = 0.5) -> bool:
        with self._lock:
            if self._is_firing:
                return False
            self._is_firing = True
            self._fire_duration = duration
            self._fire_count += 1
            logger.info(f"Laser firing for {duration}s (count: {self._fire_count})")
            return True
    
    def stop_fire(self):
        with self._lock:
            self._is_firing = False
            logger.info("Laser stopped")
    
    def set_power(self, power: float):
        with self._lock:
            self._fire_power = max(0.0, min(1.0, power))
    
    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_firing": self._is_firing,
                "power": self._fire_power,
                "fire_count": self._fire_count
            }
    
    def _laser_loop(self):
        while self._running:
            try:
                with self._lock:
                    firing = self._is_firing
                    duration = self._fire_duration
                
                if firing:
                    time.sleep(duration)
                    with self._lock:
                        self._is_firing = False
                    logger.info("Laser firing complete")
                
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Laser control error: {e}")


class MotionManager:
    def __init__(self, event_bus, config: Optional[MotionConfig] = None):
        self.event_bus = event_bus
        self.config = config or MotionConfig()
        
        self.motor_controller = MotorController(self.config, event_bus)
        self.navigation_controller = NavigationController(self.motor_controller, event_bus)
        self.laser_controller = LaserController(event_bus)
        
        self._running = False
    
    def start(self):
        self._running = True
        self.motor_controller.start()
        self.navigation_controller.start()
        self.laser_controller.start()
        logger.info("Motion manager started")
    
    def stop(self):
        self._running = False
        self.navigation_controller.stop()
        self.motor_controller.stop()
        self.laser_controller.stop()
        logger.info("Motion manager stopped")
    
    def get_status(self) -> Dict[str, Any]:
        motion_status = self.motor_controller.get_status()
        laser_status = self.laser_controller.get_status()
        
        return {
            "motor": {
                "mode": motion_status.mode.value,
                "velocity": {
                    "linear_x": motion_status.current_velocity.linear_x,
                    "angular_z": motion_status.current_velocity.angular_z
                },
                "pose": motion_status.current_pose.to_dict(),
                "motor_powers": {
                    "left": motion_status.left_motor_speed,
                    "right": motion_status.right_motor_speed
                }
            },
            "laser": laser_status,
            "navigation": {
                "target": self.navigation_controller._target_pose.to_dict() 
                         if self.navigation_controller._target_pose else None,
                "waypoints_remaining": len(self.navigation_controller._waypoints) - 
                                      self.navigation_controller._current_waypoint_index
            }
        }
    
    def emergency_stop(self):
        logger.warning("EMERGENCY STOP triggered")
        self.motor_controller.stop_motors()
        self.laser_controller.stop_fire()
        self.navigation_controller.clear_waypoints()
