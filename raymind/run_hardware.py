#!/usr/bin/env python3
"""
Farm Robot OS - 硬件版主程序
支持树莓派 + Arduino + 传感器
"""
import sys
sys.path.insert(0, '/home/meta/RayMind')

import os
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    parser = argparse.ArgumentParser(description='Farm Robot OS')
    parser.add_argument('--hardware', choices=['simulation', 'raspberry_pi', 'arduino'],
                       default='simulation', help='Hardware type')
    parser.add_argument('--port', type=int, default=8080, help='Web server port')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║       🌾 智能农田作业机器人 - 硬件版                          ║
╠══════════════════════════════════════════════════════════════╣
║  硬件模式: {args.hardware:<40}║
║  服务端口: {args.port:<40}║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # 根据硬件类型加载配置
    if args.hardware == 'raspberry_pi':
        config = {
            'hardware_type': 'raspberry_pi',
            'i2c_bus': 1,
            'lidar_port': '/dev/ttyUSB0',
            'gps_port': '/dev/ttyUSB1',
            'laser_gpio': 18,
        }
    elif args.hardware == 'arduino':
        config = {
            'hardware_type': 'arduino',
            'arduino_port': '/dev/ttyACM0',
            'lidar_port': '/dev/ttyUSB0',
        }
    else:
        config = {
            'hardware_type': 'simulation',
        }
    
    # 初始化硬件
    try:
        from farm_robot_os.hal import HardwareManager
        hw_manager = HardwareManager(config)
        
        if args.hardware != 'simulation':
            hw_manager.initialize()
            print(f"✓ 硬件初始化完成")
        else:
            print(f"✓ 模拟模式启动")
    except Exception as e:
        print(f"⚠ 硬件初始化失败: {e}")
        print(f"  切换到模拟模式")
    
    # 启动Web服务
    from farm_robot_os.web_gui import main as web_main
    
    print(f"\n启动Web服务在端口 {args.port}...")
    print(f"访问 http://localhost:{args.port}")
    
    # 替换端口
    import farm_robot_os.web_gui as web_gui
    web_gui.HTTPServer.address_port = ('', args.port)
    
    try:
        web_main()
    except KeyboardInterrupt:
        print("\n正在关闭...")
        if 'hw_manager' in dir():
            hw_manager.shutdown()


if __name__ == '__main__':
    main()
