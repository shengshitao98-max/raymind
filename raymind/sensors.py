"""
传感器数据处理模块
支持深度相机、激光雷达、GPS、IMU等传感器
"""

import threading
import time
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from queue import Queue, Empty

logger = logging.getLogger("SensorModule")


@dataclass
class SensorData:
    timestamp: datetime = field(default_factory=datetime.now)
    sensor_type: str = ""
    

@dataclass
class DepthImageData(SensorData):
    sensor_type: str = "depth_camera"
    width: int = 640
    height: int = 480
    depth_frame: np.ndarray = None
    rgb_frame: np.ndarray = None
    fx: float = 525.0
    fy: float = 525.0
    cx: float = 319.5
    cy: float = 239.5


@dataclass
class LidarScanData(SensorData):
    sensor_type: str = "lidar"
    ranges: np.ndarray = None
    angles: np.ndarray = None
    min_range: float = 0.1
    max_range: float = 30.0
    angle_min: float = -np.pi
    angle_max: float = np.pi
    num_readings: int = 360


@dataclass
class GPSData(SensorData):
    sensor_type: str = "gps"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    accuracy: float = 0.0
    speed: float = 0.0
    heading: float = 0.0
    fix_quality: int = 0


@dataclass
class IMUData(SensorData):
    sensor_type: str = "imu"
    acceleration: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    temperature: float = 25.0


@dataclass
class SensorFusionData:
    timestamp: datetime = field(default_factory=datetime.now)
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    confidence: float = 0.0


class SensorBase:
    def __init__(self, name: str, event_bus):
        self.name = name
        self.event_bus = event_bus
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._data_queue: Queue = Queue(maxsize=100)
        self._last_data: Optional[SensorData] = None
    
    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            logger.info(f"Sensor {self.name} started")
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info(f"Sensor {self.name} stopped")
    
    def _read_loop(self):
        raise NotImplementedError
    
    def get_latest_data(self, timeout: float = 0.1) -> Optional[SensorData]:
        try:
            return self._data_queue.get(timeout=timeout)
        except Empty:
            return self._last_data


class DepthCameraSensor(SensorBase):
    def __init__(self, event_bus, model_path: str = "best.pt", resolution: Tuple[int, int] = (640, 480)):
        super().__init__("DepthCamera", event_bus)
        self.resolution = resolution
        self.model_path = model_path
        self._detection_model = None
        self._confidence_threshold = 0.5
    
    def _read_loop(self):
        while self._running:
            try:
                data = self._simulate_depth_camera()
                self._last_data = data
                self._data_queue.put(data)
                time.sleep(0.033)
            except Exception as e:
                logger.error(f"Depth camera error: {e}")
                time.sleep(1.0)
    
    def _simulate_depth_camera(self) -> DepthImageData:
        data = DepthImageData(
            width=self.resolution[0],
            height=self.resolution[1],
            depth_frame=np.random.randint(0, 65535, (self.resolution[1], self.resolution[0]), dtype=np.uint16),
            rgb_frame=np.random.randint(0, 255, (self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
        )
        return data
    
    def set_confidence_threshold(self, threshold: float):
        self._confidence_threshold = max(0.0, min(1.0, threshold))
    
    def detect_objects(self, depth_data: DepthImageData) -> List[Dict[str, Any]]:
        detections = []
        num_detections = np.random.randint(0, 5)
        
        for i in range(num_detections):
            x = np.random.randint(50, depth_data.width - 50)
            y = np.random.randint(50, depth_data.height - 50)
            w = np.random.randint(30, 100)
            h = np.random.randint(30, 100)
            
            detections.append({
                "class": "weed",
                "confidence": np.random.uniform(0.5, 0.99),
                "bbox": [x, y, x + w, y + h],
                "center": (x + w // 2, y + h // 2),
                "depth": np.random.uniform(0.5, 5.0)
            })
        
        return [d for d in detections if d["confidence"] >= self._confidence_threshold]


class LidarSensor(SensorBase):
    def __init__(self, event_bus, num_readings: int = 360, max_range: float = 30.0):
        super().__init__("Lidar", event_bus)
        self.num_readings = num_readings
        self.max_range = max_range
        self._obstacle_threshold = 0.5
    
    def _read_loop(self):
        while self._running:
            try:
                data = self._simulate_lidar_scan()
                self._last_data = data
                self._data_queue.put(data)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Lidar error: {e}")
                time.sleep(1.0)
    
    def _simulate_lidar_scan(self) -> LidarScanData:
        angles = np.linspace(-np.pi, np.pi, self.num_readings)
        ranges = np.random.uniform(0.5, self.max_range, self.num_readings)
        ranges = np.clip(ranges, 0.1, self.max_range)
        
        return LidarScanData(
            ranges=ranges,
            angles=angles,
            num_readings=self.num_readings,
            min_range=0.1,
            max_range=self.max_range,
            angle_min=-np.pi,
            angle_max=np.pi
        )
    
    def get_obstacles(self, scan_data: LidarScanData) -> List[Tuple[float, float]]:
        obstacles = []
        if scan_data.ranges is None:
            return obstacles
        
        for i, r in enumerate(scan_data.ranges):
            if r < self.max_range and r > 0.1:
                angle = scan_data.angles[i]
                x = r * np.cos(angle)
                y = r * np.sin(angle)
                obstacles.append((x, y))
        
        return obstacles
    
    def is_path_clear(self, scan_data: LidarScanData, angle: float, distance: float) -> bool:
        if scan_data.ranges is None:
            return True
        
        target_idx = int((angle - scan_data.angle_min) / (scan_data.angle_max - scan_data.angle_min) * 
                        (scan_data.num_readings - 1))
        target_idx = max(0, min(scan_data.num_readings - 1, target_idx))
        
        return scan_data.ranges[target_idx] > distance


class GPSSensor(SensorBase):
    def __init__(self, event_bus):
        super().__init__("GPS", event_bus)
        self._base_lat = 0.0
        self._base_lon = 0.0
    
    def _read_loop(self):
        while self._running:
            try:
                data = self._simulate_gps()
                self._last_data = data
                self._data_queue.put(data)
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"GPS error: {e}")
                time.sleep(1.0)
    
    def _simulate_gps(self) -> GPSData:
        return GPSData(
            latitude=self._base_lat + np.random.uniform(-0.0001, 0.0001),
            longitude=self._base_lon + np.random.uniform(-0.0001, 0.0001),
            altitude=np.random.uniform(10, 50),
            accuracy=np.random.uniform(0.5, 5.0),
            speed=np.random.uniform(0, 2.0),
            heading=np.random.uniform(0, 360),
            fix_quality=4
        )
    
    def set_base_position(self, lat: float, lon: float):
        self._base_lat = lat
        self._base_lon = lon


class IMUSensor(SensorBase):
    def __init__(self, event_bus):
        super().__init__("IMU", event_bus)
        self._orientation_offset = (0.0, 0.0, 0.0)
    
    def _read_loop(self):
        while self._running:
            try:
                data = self._simulate_imu()
                self._last_data = data
                self._data_queue.put(data)
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"IMU error: {e}")
                time.sleep(1.0)
    
    def _simulate_imu(self) -> IMUData:
        return IMUData(
            acceleration=(
                np.random.normal(0, 0.1),
                np.random.normal(0, 0.1),
                np.random.normal(9.8, 0.1)
            ),
            angular_velocity=(
                np.random.normal(0, 0.01),
                np.random.normal(0, 0.01),
                np.random.normal(0, 0.01)
            ),
            orientation=(
                np.random.uniform(-0.1, 0.1) + self._orientation_offset[0],
                np.random.uniform(-0.1, 0.1) + self._orientation_offset[1],
                np.random.uniform(-0.1, 0.1) + self._orientation_offset[2]
            ),
            temperature=np.random.uniform(25, 35)
        )
    
    def calibrate(self, samples: int = 100):
        acc_samples = []
        for _ in range(samples):
            data = self.get_latest_data()
            if data:
                acc_samples.append(data.acceleration)
            time.sleep(0.01)
        
        if acc_samples:
            avg_acc = np.mean(acc_samples, axis=0)
            self._orientation_offset = (
                -avg_acc[0],
                -avg_acc[1],
                -(avg_acc[2] - 9.8)
            )
            logger.info(f"IMU calibrated with offset: {self._orientation_offset}")


class SensorManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._sensors: Dict[str, SensorBase] = {}
        self._running = False
        self._fusion_thread: Optional[threading.Thread] = None
    
    def register_sensor(self, sensor: SensorBase):
        self._sensors[sensor.name] = sensor
        logger.info(f"Registered sensor: {sensor.name}")
    
    def start_all(self):
        self._running = True
        for sensor in self._sensors.values():
            sensor.start()
        self._fusion_thread = threading.Thread(target=self._sensor_fusion_loop, daemon=True)
        self._fusion_thread.start()
        logger.info("All sensors started")
    
    def stop_all(self):
        self._running = False
        for sensor in self._sensors.values():
            sensor.stop()
        logger.info("All sensors stopped")
    
    def get_sensor(self, name: str) -> Optional[SensorBase]:
        return self._sensors.get(name)
    
    def _sensor_fusion_loop(self):
        while self._running:
            try:
                fusion_data = self._perform_fusion()
                if fusion_data:
                    pass
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Sensor fusion error: {e}")
    
    def _perform_fusion(self) -> Optional[SensorFusionData]:
        gps_data = self._sensors.get("GPS")
        imu_data = self._sensors.get("IMU")
        
        if not gps_data or not imu_data:
            return None
        
        gps = gps_data.get_latest_data(timeout=0.5)
        imu = imu_data.get_latest_data(timeout=0.1)
        
        if not gps or not imu:
            return None
        
        return SensorFusionData(
            position=(gps.latitude, gps.longitude, gps.altitude),
            orientation=imu.orientation,
            velocity=(gps.speed * np.cos(np.radians(gps.heading)),
                     gps.speed * np.sin(np.radians(gps.heading)),
                     0),
            confidence=0.8
        )
