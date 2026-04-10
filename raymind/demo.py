#!/usr/bin/env python3
"""
Farm Robot Operating System Demo
智能农田作业机器人操作系统演示
"""

import sys
import time
import logging
from farm_robot_os import FarmRobotController, RobotAPI, TaskPriority

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def demo_basic_operations():
    print("\n" + "="*60)
    print("Farm Robot OS - Basic Operations Demo")
    print("="*60 + "\n")
    
    config = {
        "max_linear_speed": 1.5,
        "max_angular_speed": 1.0,
        "wheel_base": 0.5,
        "wheel_radius": 0.15,
        "model_path": "best.pt"
    }
    
    controller = FarmRobotController(config)
    api = RobotAPI(controller)
    
    print("1. Initializing Robot...")
    result = api.start()
    print(f"   Result: {result}")
    print()
    
    print("2. Getting Robot Status...")
    status = api.status()
    print(f"   State: {status['state']}")
    print(f"   Battery: {status['battery_level']:.1f}%")
    print(f"   Position: ({status['position']['x']}, {status['position']['y']})")
    print()
    
    time.sleep(2)
    
    print("3. Getting Sensor Data...")
    sensor_data = api.sensor_data()
    for sensor, data in sensor_data.items():
        print(f"   {sensor}: {data}")
    print()
    
    time.sleep(1)
    
    print("4. Navigating to position (5.0, 3.0)...")
    result = api.navigate(5.0, 3.0)
    print(f"   Result: {result}")
    time.sleep(3)
    print()
    
    print("5. Starting Scan Task (10 seconds)...")
    result = api.scan(duration=10)
    print(f"   Result: {result}")
    time.sleep(3)
    print()
    
    print("6. Getting Detected Targets...")
    targets = api.targets()
    print(f"   Targets found: {len(targets['targets'])}")
    for i, target in enumerate(targets['targets'][:3]):
        print(f"   Target {i+1}: type={target['type']}, confidence={target['confidence']:.2f}")
    print()
    
    print("7. Starting Patrol Mission...")
    waypoints = [
        {"x": 0, "y": 0},
        {"x": 5, "y": 0},
        {"x": 5, "y": 5},
        {"x": 0, "y": 5}
    ]
    result = api.patrol(waypoints)
    print(f"   Result: {result}")
    time.sleep(3)
    print()
    
    print("8. Checking Tasks...")
    tasks = api.tasks()
    print(f"   Active tasks: {len(tasks['tasks'])}")
    for task in tasks['tasks'][:3]:
        print(f"   - {task['task_type']}: {task['status']} ({task['progress']:.1f}%)")
    print()
    
    print("9. Getting Motion Status...")
    motion_status = api.motion_status()
    print(f"   Motor velocity: linear={motion_status['motor']['velocity']['linear_x']:.2f}, angular={motion_status['motor']['velocity']['angular_z']:.2f}")
    print(f"   Laser: {motion_status['laser']}")
    print()
    
    print("10. Emergency Stop Demo...")
    result = api.emergency()
    print(f"    Result: {result}")
    
    time.sleep(1)
    
    status = api.status()
    print(f"    State after emergency: {status['state']}")
    print()
    
    print("11. Resuming from Emergency...")
    result = api.resume()
    print(f"    Result: {result}")
    
    status = api.status()
    print(f"    State after resume: {status['state']}")
    print()
    
    print("12. Shutting Down...")
    result = api.stop()
    print(f"    Result: {result}")
    print()
    
    print("Demo completed successfully!")
    print("="*60)


def demo_target_eradication():
    print("\n" + "="*60)
    print("Farm Robot OS - Target Eradication Demo")
    print("="*60 + "\n")
    
    config = {"model_path": "best.pt"}
    controller = FarmRobotController(config)
    api = RobotAPI(controller)
    
    print("Initializing robot...")
    api.start()
    time.sleep(2)
    
    print("\nScanning for weeds/targets...")
    targets_data = api.targets()
    print(f"Found {len(targets_data['targets'])} targets")
    
    if targets_data['targets']:
        print("\nExecuting eradication mission...")
        result = api.eradicate(targets_data['targets'])
        print(f"Task submitted: {result}")
    else:
        print("\nNo targets found, creating demo targets...")
        demo_targets = [
            {"x": 1.0, "y": 1.0, "type": "weed", "confidence": 0.85},
            {"x": 2.0, "y": 1.5, "type": "weed", "confidence": 0.92},
            {"x": 1.5, "y": 2.0, "type": "weed", "confidence": 0.78}
        ]
        result = api.eradicate(demo_targets)
        print(f"Task submitted: {result}")
    
    time.sleep(5)
    
    tasks = api.tasks()
    print(f"\nTask status: {tasks}")
    
    print("\nShutting down...")
    api.stop()
    print("="*60)


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--eradication":
            demo_target_eradication()
        else:
            print("Usage: python demo.py [--eradication]")
            demo_basic_operations()
    else:
        demo_basic_operations()


if __name__ == "__main__":
    main()
