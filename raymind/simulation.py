#!/usr/bin/env python3
"""
RayMind 仿真模拟系统
提供机器人运动、传感器、环境的仿真
"""

import math
import random
import time
import threading
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum


class EnvironmentType(Enum):
    """环境类型"""
    FARMLAND = "farmland"
    GREENHOUSE = "greenhouse"
    ORCHARD = "orchard"
    WAREHOUSE = "warehouse"


@dataclass
class Point2D:
    """2D点"""
    x: float = 0.0
    y: float = 0.0


@dataclass
class Pose:
    """机器人位姿"""
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0


@dataclass
class RobotState:
    """机器人状态"""
    pose: Pose = field(default_factory=Pose)
    velocity_linear: float = 0.0
    velocity_angular: float = 0.0
    left_track: float = 0.0
    right_track: float = 0.0
    battery: float = 100.0


@dataclass
class Obstacle:
    """障碍物"""
    x: float
    y: float
    radius: float
    type: str = "weed"


@dataclass
class FarmEnvironment:
    """农田环境"""
    width: float = 50.0
    height: float = 100.0
    row_spacing: float = 1.5
    plant_spacing: float = 0.3
    obstacles: List[Obstacle] = field(default_factory=list)
    environment_type: EnvironmentType = EnvironmentType.FARMLAND
    
    def __post_init__(self):
        self._generate_obstacles()
    
    def _generate_obstacles(self):
        """生成障碍物（杂草等）"""
        random.seed(42)
        
        for row in range(int(self.height / self.row_spacing)):
            for col in range(int(self.width / self.plant_spacing)):
                if random.random() < 0.3:
                    x = col * self.plant_spacing + random.uniform(-0.1, 0.1)
                    y = row * self.row_spacing + random.uniform(-0.1, 0.1)
                    
                    weed_types = ["牛筋草", "马唐", "稗草", "狗尾草", "香附子"]
                    obstacle = Obstacle(
                        x=x - self.width / 2,
                        y=y - self.height / 2,
                        radius=random.uniform(0.05, 0.15),
                        type=random.choice(weed_types)
                    )
                    self.obstacles.append(obstacle)
        
        for i in range(5):
            obstacle = Obstacle(
                x=random.uniform(-self.width/2 + 1, self.width/2 - 1),
                y=random.uniform(-self.height/2 + 1, self.height/2 - 1),
                radius=random.uniform(0.3, 0.8),
                type="rock"
            )
            self.obstacles.append(obstacle)


class RobotPhysics:
    """机器人物理模型"""
    
    def __init__(self,
                 wheel_base: float = 0.5,
                 wheel_radius: float = 0.15,
                 max_linear_speed: float = 1.0,
                 max_angular_speed: float = 2.0):
        self.wheel_base = wheel_base
        self.wheel_radius = wheel_radius
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed
        
        self.state = RobotState()
        self.noise_enabled = True
    
    def set_velocity(self, linear: float, angular: float):
        """设置速度"""
        self.state.velocity_linear = max(-self.max_linear_speed, 
                                         min(self.max_linear_speed, linear))
        self.state.velocity_angular = max(-self.max_angular_speed,
                                          min(self.max_angular_speed, angular))
    
    def set_track(self, left: float, right: float):
        """设置履带速度"""
        self.state.left_track = max(-100, min(100, left))
        self.state.right_track = max(-100, min(100, right))
        
        v_left = self.state.left_track / 100 * self.max_linear_speed
        v_right = self.state.right_track / 100 * self.max_linear_speed
        
        self.state.velocity_linear = (v_left + v_right) / 2
        self.state.velocity_angular = (v_right - v_left) / self.wheel_base
    
    def update(self, dt: float):
        """更新机器人状态"""
        v = self.state.velocity_linear
        omega = self.state.velocity_angular
        
        if self.noise_enabled:
            v += random.gauss(0, 0.01)
            omega += random.gauss(0, 0.02)
        
        self.state.pose.x += v * math.cos(self.state.pose.yaw) * dt
        self.state.pose.y += v * math.sin(self.state.pose.yaw) * dt
        self.state.pose.yaw += omega * dt
        
        self.state.pose.yaw = math.atan2(math.sin(self.state.pose.yaw), 
                                         math.cos(self.state.pose.yaw))
        
        if self.state.battery > 0:
            self.state.battery -= abs(v) * 0.5 * dt


class LiDARSimulator:
    """激光雷达仿真"""
    
    def __init__(self,
                 num_rays: int = 360,
                 min_range: float = 0.1,
                 max_range: float = 30.0,
                 field_of_view: float = math.pi):
        self.num_rays = num_rays
        self.min_range = min_range
        self.max_range = max_range
        self.field_of_view = field_of_view
        
        self.angle_min = -field_of_view / 2
        self.angle_max = field_of_view / 2
        self.angle_increment = field_of_view / num_rays
    
    def scan(self, pose: Pose, environment: FarmEnvironment) -> List[float]:
        """扫描"""
        ranges = []
        
        for i in range(self.num_rays):
            angle = self.angle_min + i * self.angle_increment
            ray_angle = pose.yaw + angle
            
            range_val = self._cast_ray(pose.x, pose.y, ray_angle, environment)
            ranges.append(range_val)
        
        return ranges
    
    def _cast_ray(self, x: float, y: float, angle: float, 
                  environment: FarmEnvironment) -> float:
        """射线投射"""
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        max_dist = self.max_range
        step = 0.05
        
        for d in range(0, int(max_dist / step)):
            px = x + dx * d * step
            py = y + dy * d * step
            
            if abs(px) > environment.width / 2 or abs(py) > environment.height / 2:
                return d * step
            
            for obstacle in environment.obstacles:
                dist = math.sqrt((px - obstacle.x) ** 2 + (py - obstacle.y) ** 2)
                if dist < obstacle.radius:
                    return dist
        
        return max_dist


class CameraSimulator:
    """相机仿真"""
    
    def __init__(self,
                 width: int = 640,
                 height: int = 480,
                 fov: float = math.pi / 3):
        self.width = width
        self.height = height
        self.fov = fov
    
    def capture(self, pose: Pose, environment: FarmEnvironment) -> Dict:
        """捕获图像"""
        visible_obstacles = []
        
        for obstacle in environment.obstacles:
            dx = obstacle.x - pose.x
            dy = obstacle.y - pose.y
            dist = math.sqrt(dx * dx + dy * dy)
            
            if dist < 10.0:
                angle_to = math.atan2(dy, dx)
                angle_diff = angle_to - pose.yaw
                
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                if abs(angle_diff) < self.fov / 2:
                    visible_obstacles.append({
                        'type': obstacle.type,
                        'distance': dist,
                        'angle': angle_diff,
                        'size': obstacle.radius
                    })
        
        return {
            'width': self.width,
            'height': self.height,
            'obstacles': visible_obstacles,
            'timestamp': time.time()
        }


class IMUSimulator:
    """IMU仿真"""
    
    def __init__(self):
        self.noise_level = 0.01
    
    def get_data(self, pose: Pose, velocity_linear: float, 
                 velocity_angular: float) -> Dict:
        """获取IMU数据"""
        noise = self.noise_level
        
        roll = random.gauss(0, noise)
        pitch = random.gauss(0, noise)
        yaw = pose.yaw + random.gauss(0, noise)
        
        ax = velocity_linear * math.cos(pose.yaw) * 0.1 + random.gauss(0, noise)
        ay = velocity_linear * math.sin(pose.yaw) * 0.1 + random.gauss(0, noise)
        az = 9.81 + random.gauss(0, noise)
        
        gx = velocity_angular + random.gauss(0, noise)
        gy = random.gauss(0, noise)
        gz = random.gauss(0, noise)
        
        return {
            'orientation': {'roll': roll, 'pitch': pitch, 'yaw': yaw},
            'angular_velocity': {'x': gx, 'y': gy, 'z': gz},
            'linear_acceleration': {'x': ax, 'y': ay, 'z': az},
            'timestamp': time.time()
        }


class GPSSimulator:
    """GPS仿真"""
    
    def __init__(self, base_lat: float = 31.0, base_lon: float = 121.0):
        self.base_lat = base_lat
        self.base_lon = base_lon
        self.noise_level = 0.00001
    
    def get_position(self, x: float, y: float) -> Dict:
        """获取GPS位置"""
        lat_per_m = 1.0 / 111320.0
        lon_per_m = 1.0 / (111320.0 * math.cos(math.radians(self.base_lat)))
        
        latitude = self.base_lat + y * lat_per_m + random.gauss(0, self.noise_level)
        longitude = self.base_lon + x * lon_per_m + random.gauss(0, self.noise_level)
        altitude = random.gauss(10, 0.5)
        
        return {
            'latitude': latitude,
            'longitude': longitude,
            'altitude': altitude,
            'timestamp': time.time()
        }


class RayMindSimulator:
    """RayMind综合仿真器"""
    
    def __init__(self, environment: FarmEnvironment = None):
        self.environment = environment or FarmEnvironment()
        self.physics = RobotPhysics()
        self.lidar = LiDARSimulator()
        self.camera = CameraSimulator()
        self.imu = IMUSimulator()
        self.gps = GPSSimulator()
        
        self.running = False
        self.simulation_thread = None
        self.dt = 0.05
        
        self.callbacks = {
            'scan': [],
            'camera': [],
            'imu': [],
            'gps': [],
            'odom': [],
            'battery': []
        }
    
    def start(self):
        """启动仿真"""
        if self.running:
            return
        
        self.running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop, 
                                                 daemon=True)
        self.simulation_thread.start()
    
    def stop(self):
        """停止仿真"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=2.0)
    
    def _simulation_loop(self):
        """仿真循环"""
        while self.running:
            self.physics.update(self.dt)
            
            scan_data = self.lidar.scan(self.physics.state.pose, self.environment)
            camera_data = self.camera.capture(self.physics.state.pose, self.environment)
            imu_data = self.imu.get_data(self.physics.state.pose,
                                         self.physics.state.velocity_linear,
                                         self.physics.state.velocity_angular)
            gps_data = self.gps.get_position(self.physics.state.pose.x,
                                           self.physics.state.pose.y)
            
            for callback in self.callbacks['scan']:
                callback(scan_data)
            for callback in self.callbacks['camera']:
                callback(camera_data)
            for callback in self.callbacks['imu']:
                callback(imu_data)
            for callback in self.callbacks['gps']:
                callback(gps_data)
            
            odom_data = {
                'pose': {
                    'x': self.physics.state.pose.x,
                    'y': self.physics.state.pose.y,
                    'yaw': self.physics.state.pose.yaw
                },
                'velocity': {
                    'linear': self.physics.state.velocity_linear,
                    'angular': self.physics.state.velocity_angular
                }
            }
            for callback in self.callbacks['odom']:
                callback(odom_data)
            
            battery_data = {'percentage': self.physics.state.battery}
            for callback in self.callbacks['battery']:
                callback(battery_data)
            
            time.sleep(self.dt)
    
    def set_velocity(self, linear: float, angular: float):
        """设置速度"""
        self.physics.set_velocity(linear, angular)
    
    def set_track(self, left: float, right: float):
        """设置履带"""
        self.physics.set_track(left, right)
    
    def get_state(self) -> Dict:
        """获取状态"""
        return {
            'pose': {
                'x': self.physics.state.pose.x,
                'y': self.physics.state.pose.y,
                'yaw': self.physics.state.pose.yaw
            },
            'velocity': {
                'linear': self.physics.state.velocity_linear,
                'angular': self.physics.state.velocity_angular
            },
            'battery': self.physics.state.battery,
            'obstacles': len(self.environment.obstacles)
        }
    
    def register_callback(self, event: str, callback):
        """注册回调"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def get_visualization_data(self) -> Dict:
        """获取可视化数据"""
        return {
            'robot': {
                'x': self.physics.state.pose.x,
                'y': self.physics.state.pose.y,
                'yaw': self.physics.state.pose.yaw
            },
            'obstacles': [(o.x, o.y, o.radius, o.type) 
                         for o in self.environment.obstacles],
            'environment': {
                'width': self.environment.width,
                'height': self.environment.height
            }
        }


def create_farm_simulation() -> RayMindSimulator:
    """创建农田仿真"""
    env = FarmEnvironment(
        width=50.0,
        height=100.0,
        row_spacing=1.5,
        plant_spacing=0.3,
        environment_type=EnvironmentType.FARMLAND
    )
    return RayMindSimulator(env)


if __name__ == '__main__':
    print("RayMind Simulation Test")
    print("=" * 40)
    
    sim = create_farm_simulation()
    sim.start()
    
    try:
        for i in range(100):
            sim.set_velocity(0.3, 0.2)
            state = sim.get_state()
            print(f"{i:3d}. 位置: ({state['pose']['x']:.2f}, {state['pose']['y']:.2f}) "
                  f"电池: {state['battery']:.1f}%")
            time.sleep(0.1)
    finally:
        sim.stop()
    
    print("\nSimulation completed!")
