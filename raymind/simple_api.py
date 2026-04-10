#!/usr/bin/env python3
"""
Farm Robot OS - Simple API
简化版API，避开复杂的异步和锁机制
"""
import sys
sys.path.insert(0, '/home/meta/RayMind')

import time
import random
from enum import Enum

class RobotState(Enum):
    IDLE = "idle"
    READY = "ready"
    NAVIGATING = "navigating"
    SCANNING = "scanning"
    EXECUTING = "executing"
    ERROR = "error"

class FarmRobot:
    def __init__(self, model_path="best.pt"):
        self.state = RobotState.IDLE
        self.position = {"x": 0.0, "y": 0.0, "yaw": 0.0}
        self.battery = 100.0
        self.model_path = model_path
        self.targets = []
        
    def start(self):
        print("正在初始化机器人...")
        time.sleep(0.5)
        self.state = RobotState.READY
        print(f"机器人就绪 | 位置: ({self.position['x']}, {self.position['y']})")
        return True
    
    def stop(self):
        print("关闭机器人...")
        self.state = RobotState.IDLE
        return True
    
    def get_status(self):
        return {
            "state": self.state.value,
            "position": self.position,
            "battery": self.battery
        }
    
    def navigate_to(self, x, y):
        if self.state != RobotState.READY:
            print(f"当前状态 {self.state.value} 无法导航")
            return False
        
        print(f"导航到目标点 ({x}, {y})...")
        self.state = RobotState.NAVIGATING
        
        dx = x - self.position["x"]
        dy = y - self.position["y"]
        distance = (dx**2 + dy**2) ** 0.5
        time.sleep(min(distance * 0.5, 2.0))
        
        self.position["x"] = x
        self.position["y"] = y
        self.state = RobotState.READY
        print(f"到达目标 | 新位置: ({x}, {y})")
        return True
    
    def scan(self, duration=10):
        if self.state != RobotState.READY:
            print(f"当前状态 {self.state.value} 无法扫描")
            return []
        
        print(f"开始扫描 ({duration}秒)...")
        self.state = RobotState.SCANNING
        
        for i in range(duration):
            time.sleep(1)
            print(f"  扫描进度: {i+1}/{duration}")
        
        num_targets = random.randint(2, 6)
        self.targets = []
        for i in range(num_targets):
            self.targets.append({
                "id": i+1,
                "x": random.uniform(-5, 5),
                "y": random.uniform(-5, 5),
                "type": "weed",
                "confidence": random.uniform(0.6, 0.99)
            })
        
        self.state = RobotState.READY
        print(f"扫描完成 | 发现 {len(self.targets)} 个目标")
        return self.targets
    
    def get_targets(self):
        return self.targets
    
    def eradicate(self, targets=None):
        if targets is None:
            targets = self.targets
        
        if self.state != RobotState.READY:
            print(f"当前状态 {self.state.value} 无法执行")
            return 0
        
        if not targets:
            print("没有目标需要清除")
            return 0
        
        print(f"开始清除 {len(targets)} 个目标...")
        self.state = RobotState.EXECUTING
        
        count = 0
        for target in targets:
            x, y = target.get("x", 0), target.get("y", 0)
            print(f"  清除目标 {target.get('id', '?')} at ({x:.2f}, {y:.2f})")
            
            self.navigate_to(x, y)
            time.sleep(0.5)
            
            power = target.get("confidence", 0.8) * 100
            print(f"    激光发射 (功率: {power:.0f}%)")
            time.sleep(0.3)
            
            count += 1
        
        self.state = RobotState.READY
        print(f"清除完成 | 清除 {count} 个目标")
        return count
    
    def patrol(self, waypoints):
        if self.state != RobotState.READY:
            print("无法执行巡逻")
            return False
        
        print(f"开始巡逻 ({len(waypoints)} 个路径点)...")
        
        for i, wp in enumerate(waypoints):
            x, y = wp.get("x", 0), wp.get("y", 0)
            print(f"  路径点 {i+1}: ({x}, {y})")
            self.navigate_to(x, y)
            time.sleep(0.5)
        
        print("巡逻完成")
        return True


def demo():
    print("=" * 50)
    print("  智能农田作业机器人 - 操作演示")
    print("=" * 50)
    
    robot = FarmRobot("best.pt")
    
    print("\n[1] 启动系统")
    robot.start()
    
    print("\n[2] 获取状态")
    status = robot.get_status()
    print(f"    状态: {status['state']}")
    print(f"    电池: {status['battery']:.1f}%")
    
    print("\n[3] 导航测试")
    robot.navigate_to(3.0, 2.0)
    
    print("\n[4] 扫描测试")
    targets = robot.scan(duration=5)
    for t in targets:
        print(f"    - {t['type']}: 置信度 {t['confidence']:.2f}")
    
    print("\n[5] 目标清除")
    robot.eradicate(targets[:2])
    
    print("\n[6] 巡逻任务")
    waypoints = [
        {"x": 0, "y": 0},
        {"x": 5, "y": 0},
        {"x": 5, "y": 5},
        {"x": 0, "y": 5},
        {"x": 0, "y": 0}
    ]
    robot.patrol(waypoints)
    
    print("\n[7] 关闭系统")
    robot.stop()
    
    print("\n" + "=" * 50)
    print("  演示完成!")
    print("=" * 50)

if __name__ == "__main__":
    demo()
