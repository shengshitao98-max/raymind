#!/usr/bin/env python3
"""
Farm Robot OS 使用示例
"""
import sys
sys.path.insert(0, '/home/meta/RayMind')

from farm_robot_os import FarmRobotController, RobotAPI, TaskPriority

def main():
    config = {
        "model_path": "best.pt",
        "max_linear_speed": 1.5,
        "max_angular_speed": 1.0,
        "wheel_base": 0.5,
    }
    
    print("=== 智能农田作业机器人系统 ===\n")
    
    print("1. 创建控制器...")
    controller = FarmRobotController(config)
    api = RobotAPI(controller)
    
    print("2. 初始化系统...")
    result = api.start()
    print(f"   初始化结果: {result.get('success', False)}")
    
    if result.get('success'):
        print("\n3. 获取机器人状态...")
        status = api.status()
        print(f"   状态: {status['state']}")
        print(f"   电池: {status['battery_level']:.1f}%")
        print(f"   位置: ({status['position']['x']}, {status['position']['y']})")
        
        print("\n4. 传感器数据...")
        sensor_data = api.sensor_data()
        for sensor, data in sensor_data.items():
            print(f"   - {sensor}: OK")
        
        print("\n5. 示例操作:")
        
        print("   [a] 导航到目标点 (5, 3)...")
        api.navigate(5.0, 3.0)
        
        print("   [b] 扫描杂草...")
        api.scan(duration=10)
        
        print("   [c] 巡逻任务...")
        waypoints = [
            {"x": 0, "y": 0},
            {"x": 5, "y": 0},
            {"x": 5, "y": 5},
            {"x": 0, "y": 5}
        ]
        api.patrol(waypoints)
        
        print("   [d] 杂草清除任务...")
        targets = [
            {"x": 1.0, "y": 1.0, "type": "weed", "confidence": 0.9},
            {"x": 2.0, "y": 1.5, "type": "weed", "confidence": 0.85}
        ]
        api.eradicate(targets)
        
        print("\n6. 急停演示...")
        api.emergency()
        api.resume()
        
        print("\n7. 关闭系统...")
        api.stop()
        
        print("\n=== 操作完成 ===")
    else:
        print("初始化失败!")

if __name__ == "__main__":
    main()
