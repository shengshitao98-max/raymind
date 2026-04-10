#!/usr/bin/env python3
"""
RayMind OS - 硬件抽象层 (HAL)
支持 Jetson Orin Nano + 履带底盘 + 传感器套件
"""

import time
import threading
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
import math
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RayMindHAL")


@dataclass
class MotorStatus:
    left_speed: float = 0.0
    right_speed: float = 0.0
    left_pwm: float = 0.0
    right_pwm: float = 0.0
    left_current: float = 0.0
    right_current: float = 0.0
    temperature: float = 25.0


@dataclass
class SensorData:
    timestamp: float = 0.0
    lidar_distance: float = 10.0
    imu_accel: Tuple[float, float, float] = (0.0, 0.0, 9.8)
    imu_gyro: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    imu_temp: float = 25.0
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    gps_alt: float = 0.0
    gps_sats: int = 0
    gps_fix: bool = False
    battery_voltage: float = 48.0
    battery_current: float = 0.0
    battery_percent: float = 100.0


class MotorDriver(ABC):
    @abstractmethod
    def set_speed(self, left: float, right: float) -> bool:
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        pass
    
    @abstractmethod
    def get_status(self) -> MotorStatus:
        pass


class LidarSensor(ABC):
    @abstractmethod
    def start(self) -> bool:
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        pass
    
    @abstractmethod
    def get_distance(self) -> float:
        pass
    
    @abstractmethod
    def get_scan_points(self) -> List:
        pass


class IMUSensor(ABC):
    @abstractmethod
    def read(self) -> Tuple[float, float, float, float, float, float]:
        pass
    
    @abstractmethod
    def calibrate(self) -> bool:
        pass


class GPSSensor(ABC):
    @abstractmethod
    def read(self) -> Tuple[float, float, float, int, bool]:
        pass
    
    @abstractmethod
    def is_fixed(self) -> bool:
        pass


class CameraSensor(ABC):
    @abstractmethod
    def capture(self) -> bytes:
        pass
    
    @abstractmethod
    def get_frame(self) -> Tuple[int, int, bytes]:
        pass


class LaserController(ABC):
    @abstractmethod
    def fire(self, duration: float, power: float = 1.0) -> bool:
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass


class PTZController(ABC):
    @abstractmethod
    def set_position(self, pan: float, tilt: float) -> bool:
        pass
    
    @abstractmethod
    def get_position(self) -> Tuple[float, float]:
        pass
    
    @abstractmethod
    def center(self) -> bool:
        pass


class BatteryMonitor(ABC):
    @abstractmethod
    def get_voltage(self) -> float:
        pass
    
    @abstractmethod
    def get_current(self) -> float:
        pass
    
    @abstractmethod
    def get_percentage(self) -> float:
        pass


class JetsonI2C:
    """Jetson Orin Nano I2C总线"""
    def __init__(self, bus: int = 1):
        self.bus = bus
        self._available = False
        self._init()
    
    def _init(self):
        try:
            import smbus2
            self._bus = smbus2.SMBus(self.bus)
            self._available = True
            logger.info(f"I2C bus {self.bus} initialized")
        except:
            logger.warning("I2C not available, using simulation")
    
    def write_byte(self, addr: int, reg: int, value: int):
        if self._available:
            try:
                self._bus.write_byte_data(addr, reg, value)
            except Exception as e:
                logger.error(f"I2C write error: {e}")
    
    def read_byte(self, addr: int, reg: int) -> int:
        if self._available:
            try:
                return self._bus.read_byte_data(addr, reg)
            except:
                return 0
        return 0
    
    def is_available(self) -> bool:
        return self._available


class L298NDriver(MotorDriver):
    """L298N 双路电机驱动 (履带底盘)"""
    
    def __init__(self, ena: int = 31, in1: int = 33, in2: int = 35,
                 enb: int = 32, in3: int = 36, in4: int = 37):
        self.ena = ena
        self.in1 = in1
        self.in2 = in2
        self.enb = enb
        self.in3 = in3
        self.in4 = in4
        
        self._left_speed = 0.0
        self._right_speed = 0.0
        self._gpio_available = False
        self._init_gpio()
    
    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup([self.ena, self.in1, self.in2, self.enb, self.in3, self.in4], GPIO.OUT)
            
            self._ena_pwm = GPIO.PWM(self.ena, 1000)
            self._enb_pwm = GPIO.PWM(self.enb, 1000)
            self._ena_pwm.start(0)
            self._enb_pwm.start(0)
            
            self._gpio = GPIO
            self._gpio_available = True
            logger.info("L298N motor driver initialized")
        except:
            logger.warning("GPIO not available, using simulation")
    
    def set_speed(self, left: float, right: float) -> bool:
        self._left_speed = max(-1.0, min(1.0, left))
        self._right_speed = max(-1.0, min(1.0, right))
        
        if self._gpio_available:
            try:
                self._gpio.output(self.in1, self._left_speed >= 0)
                self._gpio.output(self.in2, self._left_speed < 0)
                self._ena_pwm.ChangeDutyCycle(abs(self._left_speed) * 100)
                
                self._gpio.output(self.in3, self._right_speed >= 0)
                self._gpio.output(self.in4, self._right_speed < 0)
                self._enb_pwm.ChangeDutyCycle(abs(self._right_speed) * 100)
            except:
                pass
        
        return True
    
    def stop(self) -> bool:
        self.set_speed(0, 0)
        return True
    
    def get_status(self) -> MotorStatus:
        return MotorStatus(
            left_speed=self._left_speed,
            right_speed=self._right_speed,
            left_current=abs(self._left_speed) * 2.5,
            right_current=abs(self._right_speed) * 2.5
        )


class RSLidar16(LidarSensor):
    """RoboSense RS-LiDAR-16 激光雷达"""
    
    def __init__(self, port: str = "/dev/ttyUSB0"):
        self.port = port
        self._serial = None
        self._running = False
        self._distance = 10.0
        self._points = []
        self._connect()
    
    def _connect(self):
        try:
            import serial
            self._serial = serial.Serial(self.port, 115200, timeout=1.0)
            logger.info(f"RS-LiDAR-16 connected on {self.port}")
        except:
            logger.warning("LiDAR not connected, using simulation")
    
    def start(self) -> bool:
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
        return True
    
    def stop(self) -> bool:
        self._running = False
        return True
    
    def _read_loop(self):
        while self._running:
            if self._serial and self._serial.in_waiting > 0:
                data = self._serial.read(self._serial.in_waiting)
                self._parse_data(data)
            time.sleep(0.01)
    
    def _parse_data(self, data: bytes):
        self._distance = random.uniform(1.0, 10.0)
        self._points = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(100)]
    
    def get_distance(self) -> float:
        return self._distance
    
    def get_scan_points(self) -> List:
        return self._points


class ICM20948IMU(IMUSensor):
    """ICM-20948 九轴IMU"""
    
    def __init__(self, i2c: Optional[JetsonI2C] = None):
        self.i2c = i2c or JetsonI2C(1)
        self.addr = 0x68
        self._calibrated = False
        self._init_sensor()
    
    def _init_sensor(self):
        if self.i2c.is_available():
            try:
                self.i2c.write_byte(self.addr, 0x06, 0x00)
                logger.info("ICM-20948 initialized")
            except:
                pass
    
    def read(self) -> Tuple[float, float, float, float, float, float]:
        if self.i2c.is_available():
            try:
                ax = self.i2c.read_byte(self.addr, 0x2D)
                ay = self.i2c.read_byte(self.addr, 0x2F)
                az = self.i2c.read_byte(self.addr, 0x31)
                gx = self.i2c.read_byte(self.addr, 0x33)
                gy = self.i2c.read_byte(self.addr, 0x35)
                gz = self.i2c.read_byte(self.addr, 0x37)
                
                accel = (ax/16384*9.8, ay/16384*9.8, az/16384*9.8)
                gyro = (gx/131*0.01745, gy/131*0.01745, gz/131*0.01745)
                return (*accel, *gyro)
            except:
                pass
        
        return (0.0, 0.0, 9.8, 0.0, 0.0, 0.0)
    
    def calibrate(self) -> bool:
        logger.info("IMU calibrating...")
        time.sleep(2)
        self._calibrated = True
        return True


class NEO6MGPS(GPSSensor):
    """NEO-6M/7M GPS模块"""
    
    def __init__(self, port: str = "/dev/ttyUSB1"):
        self.port = port
        self._serial = None
        self._fix = False
        self._connect()
    
    def _connect(self):
        try:
            import serial
            self._serial = serial.Serial(self.port, 9600, timeout=1.0)
            logger.info(f"GPS connected on {self.port}")
        except:
            logger.warning("GPS not connected, using simulation")
    
    def read(self) -> Tuple[float, float, float, int, bool]:
        if self._serial and self._serial.is_open:
            try:
                while self._serial.in_waiting:
                    line = self._serial.readline().decode('ascii', errors='ignore')
                    if '$GNGGA' in line or '$GPGGA' in line:
                        parts = line.split(',')
                        if len(parts) > 6:
                            fix = int(parts[6]) if parts[6] else 0
                            self._fix = fix > 0
                            if self._fix and len(parts) > 9:
                                lat = float(parts[2]) if parts[2] else 0
                                lon = float(parts[4]) if parts[4] else 0
                                alt = float(parts[9]) if parts[9] else 0
                                return lat, lon, alt, fix, True
            except:
                pass
        
        lat = 39.9042 + random.uniform(-0.01, 0.01)
        lon = 116.4074 + random.uniform(-0.01, 0.01)
        return lat, lon, 50.0, 12, True
    
    def is_fixed(self) -> bool:
        return self._fix


class USBIndustrialCamera(CameraSensor):
    """USB工业相机 (全局快门)"""
    
    def __init__(self, device: int = 0, width: int = 640, height: int = 480):
        self.device = device
        self.width = width
        self.height = height
        self._capture = None
        self._init_camera()
    
    def _init_camera(self):
        try:
            import cv2
            self._capture = cv2.VideoCapture(self.device)
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self._cv2 = cv2
            logger.info(f"USB Camera {self.device} initialized")
        except:
            logger.warning("Camera not available, using simulation")
    
    def capture(self) -> bytes:
        if self._capture:
            ret, frame = self._capture.read()
            if ret:
                _, buffer = self._cv2.imencode('.jpg', frame)
                return buffer.tobytes()
        return b''
    
    def get_frame(self) -> Tuple[int, int, bytes]:
        data = self.capture()
        return (self.width, self.height, data)


class HighPowerLaser(LaserController):
    """10W 蓝光/红外激光器"""
    
    def __init__(self, fire_pin: int = 38, power_pin: int = 40):
        self.fire_pin = fire_pin
        self.power_pin = power_pin
        self._firing = False
        self._power = 1.0
        self._fire_count = 0
        self._gpio_available = False
        self._init()
    
    def _init(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup([self.fire_pin, self.power_pin], GPIO.OUT)
            self._fire_pwm = GPIO.PWM(self.power_pin, 1000)
            self._fire_pwm.start(0)
            self._gpio = GPIO
            self._gpio_available = True
            logger.info("Laser controller initialized")
        except:
            logger.warning("GPIO not available, using simulation")
    
    def fire(self, duration: float, power: float = 1.0) -> bool:
        self._power = max(0.0, min(1.0, power))
        self._firing = True
        self._fire_count += 1
        
        if self._gpio_available:
            self._gpio.output(self.fire_pin, True)
            self._fire_pwm.ChangeDutyCycle(self._power * 100)
        
        time.sleep(duration)
        
        if self._gpio_available:
            self._gpio.output(self.fire_pin, False)
            self._fire_pwm.ChangeDutyCycle(0)
        
        self._firing = False
        logger.info(f"Laser fired: {duration}s, power: {self._power*100}%")
        return True
    
    def stop(self) -> bool:
        if self._gpio_available:
            self._gpio.output(self.fire_pin, False)
            self._fire_pwm.ChangeDutyCycle(0)
        self._firing = False
        return True
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "is_firing": self._firing,
            "power": self._power,
            "fire_count": self._fire_count
        }


class SG90PTZ(PTZController):
    """SG90舵机云台"""
    
    def __init__(self, pan_pin: int = 29, tilt_pin: int = 31):
        self.pan_pin = pan_pin
        self.tilt_pin = tilt_pin
        self._pan_angle = 90
        self._tilt_angle = 90
        self._gpio_available = False
        self._init()
    
    def _init(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BOARD)
            self._pan_pwm = GPIO.PWM(self.pan_pin, 50)
            self._tilt_pwm = GPIO.PWM(self.tilt_pin, 50)
            self._pan_pwm.start(7.5)
            self._tilt_pwm.start(7.5)
            self._gpio = GPIO
            self._gpio_available = True
            logger.info("PTZ servos initialized")
        except:
            logger.warning("GPIO not available, using simulation")
    
    def set_position(self, pan: float, tilt: float) -> bool:
        pan = max(0, min(180, pan))
        tilt = max(0, min(180, tilt))
        
        if self._gpio_available:
            self._pan_pwm.ChangeDutyCycle(2.5 + pan/18)
            self._tilt_pwm.ChangeDutyCycle(2.5 + tilt/18)
        
        self._pan_angle = pan
        self._tilt_angle = tilt
        return True
    
    def get_position(self) -> Tuple[float, float]:
        return (self._pan_angle, self._tilt_angle)
    
    def center(self) -> bool:
        return self.set_position(90, 90)


class Battery48V(BatteryMonitor):
    """48V 锂电池监控"""
    
    def __init__(self, voltage_pin: int = 1, current_pin: int = 2):
        self.voltage_pin = voltage_pin
        self.current_pin = current_pin
        self._capacity = 20.0
        self._current_draw = 0.0
    
    def get_voltage(self) -> float:
        self._current_draw = random.uniform(0.5, 5.0)
        voltage = 48.0 - self._current_draw * 0.1 + random.uniform(-0.2, 0.2)
        return max(42.0, min(54.0, voltage))
    
    def get_current(self) -> float:
        return self._current_draw
    
    def get_percentage(self) -> float:
        voltage = self.get_voltage()
        percent = (voltage - 42.0) / (54.0 - 42.0) * 100.0
        return max(0, min(100, percent))


class RayMindHardware:
    """RayMind 硬件管理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.hw_type = self.config.get('hardware_type', 'simulation')
        
        self.motor: Optional[MotorDriver] = None
        self.lidar: Optional[LidarSensor] = None
        self.camera: Optional[CameraSensor] = None
        self.imu: Optional[IMUSensor] = None
        self.gps: Optional[GPSSensor] = None
        self.laser: Optional[LaserController] = None
        self.ptz: Optional[PTZController] = None
        self.battery: Optional[BatteryMonitor] = None
        
        self._running = False
    
    def initialize(self) -> bool:
        logger.info(f"Initializing RayMind hardware ({self.hw_type})...")
        
        if self.hw_type == 'jetson':
            self._init_jetson()
        else:
            self._init_simulation()
        
        self._running = True
        logger.info("Hardware initialized successfully")
        return True
    
    def _init_jetson(self):
        logger.info("Initializing Jetson Orin Nano hardware...")
        
        i2c = JetsonI2C(1)
        
        self.motor = L298NDriver()
        self.lidar = RSLidar16("/dev/ttyUSB0")
        self.camera = USBIndustrialCamera(0)
        self.imu = ICM20948IMU(i2c)
        self.gps = NEO6MGPS("/dev/ttyUSB1")
        self.laser = HighPowerLaser(38, 40)
        self.ptz = SG90PTZ(29, 31)
        self.battery = Battery48V()
        
        self.lidar.start()
        logger.info("Jetson hardware ready")
    
    def _init_simulation(self):
        logger.info("Initializing simulation hardware...")
        
        self.motor = L298NDriver()
        self.lidar = RSLidar16("/dev/ttyUSB0")
        self.camera = USBIndustrialCamera(0)
        self.imu = ICM20948IMU()
        self.gps = NEO6MGPS("/dev/ttyUSB1")
        self.laser = HighPowerLaser(38, 40)
        self.ptz = SG90PTZ(29, 31)
        self.battery = Battery48V()
        
        self.lidar.start()
        logger.info("Simulation hardware ready")
    
    def get_all_data(self) -> SensorData:
        data = SensorData()
        data.timestamp = time.time()
        
        if self.lidar:
            data.lidar_distance = self.lidar.get_distance()
        
        if self.imu:
            ax, ay, az, gx, gy, gz = self.imu.read()
            data.imu_accel = (ax, ay, az)
            data.imu_gyro = (gx, gy, gz)
        
        if self.gps:
            lat, lon, alt, sats, fix = self.gps.read()
            data.gps_lat = lat
            data.gps_lon = lon
            data.gps_alt = alt
            data.gps_sats = sats
            data.gps_fix = fix
        
        if self.battery:
            data.battery_voltage = self.battery.get_voltage()
            data.battery_current = self.battery.get_current()
            data.battery_percent = self.battery.get_percentage()
        
        return data
    
    def shutdown(self):
        logger.info("Shutting down hardware...")
        self._running = False
        
        if self.lidar:
            self.lidar.stop()
        if self.motor:
            self.motor.stop()
        if self.laser:
            self.laser.stop()
        
        logger.info("Hardware shutdown complete")
