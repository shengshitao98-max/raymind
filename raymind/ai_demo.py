#!/usr/bin/env python3
"""
RayMind OS - AI集成演示
演示AI模块的杂草检测功能
"""
import sys
import os
import time

sys.path.insert(0, '/home/meta/RayMind')

def check_dependencies():
    missing = []
    
    try:
        import torch
    except ImportError:
        missing.append("torch")
    
    try:
        from ultralytics import YOLO
    except ImportError:
        missing.append("ultralytics")
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    return missing


def demo_ai_module():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                  RayMind AI 模块演示                            ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    missing = check_dependencies()
    
    if missing:
        print(f"⚠️  缺少依赖: {', '.join(missing)}")
        print("安装命令:")
        print("  pip install torch ultralytics opencv-python\n")
    
    print("[1] 初始化AI模块...")
    from raymind.ai import AIManager, WeedDetector, YOLOModel
    
    config = {'model_path': 'best.pt'}
    ai_manager = AIManager(config)
    print("    ✓ AI管理器已创建")
    
    print("\n[2] 测试YOLO模型...")
    yolo = YOLOModel("best.pt")
    print(f"    ✓ YOLO模型加载: {yolo.model_path}")
    print(f"    ✓ 模型可用: {yolo.available}")
    
    print("\n[3] 模拟图像检测...")
    detections = yolo.detect(None)
    print(f"    ✓ 模拟检测到 {len(detections)} 个目标")
    
    for i, det in enumerate(detections[:3]):
        print(f"      目标{i+1}: {det.class_name} - 置信度 {det.confidence:.1%}")
    
    print("\n[4] 测试杂草检测器...")
    detector = WeedDetector("best.pt")
    print(f"    ✓ 置信度阈值: {detector.confidence_threshold}")
    
    detector.set_threshold(0.7)
    print(f"    ✓ 设置阈值后: {detector.confidence_threshold}")
    
    stats = detector.get_statistics()
    print(f"    ✓ 检测统计: {stats}")
    
    print("\n[5] 测试导航AI...")
    from raymind.ai import NavigationAI
    nav = NavigationAI(grid_size=0.5)
    
    path = nav.plan_path((0, 0), (5, 5))
    print(f"    ✓ 路径规划: {len(path)} 个点")
    
    print("\n[6] 测试传感器融合...")
    from raymind.ai import SensorFusion
    fusion = SensorFusion()
    
    gps_data = {'lat': 39.9, 'lon': 116.4, 'fix': True}
    imu_data = (0.1, 0.0, 9.8, 0.0, 0.0, 0.01)
    
    pos = fusion.fuse_gps_imu(gps_data, imu_data)
    print(f"    ✓ 融合位置: {pos[:2]}")
    
    print("\n[7] 获取AI状态...")
    status = ai_manager.get_status()
    print(f"    ✓ 杂草检测器可用: {status['weed_detector']['available']}")
    print(f"    ✓ 已映射障碍物: {status['navigation']['obstacles_mapped']}")
    
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    AI 模块功能总结                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  🎯 杂草检测                                                    ║
║     - YOLO目标检测模型                                         ║
║     - 置信度阈值可调                                           ║
║     - 深度估计集成                                            ║
║                                                                  ║
║  🧭 智能导航                                                    ║
║     - A*路径规划                                               ║
║     - 障碍物规避                                               ║
║     - 传感器融合                                               ║
║                                                                  ║
║  👁️ 环境感知                                                    ║
║     - 激光雷达数据处理                                         ║
║     - 深度相机集成                                            ║
║     - GPS+IMU融合                                              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def demo_with_camera():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║               RayMind AI 实时检测演示                           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        import cv2
        from raymind.ai import WeedDetector
        
        detector = WeedDetector("best.pt")
        
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ 无法打开摄像头")
            print("使用模拟数据...")
            demo_ai_module()
            return
        
        print("📷 摄像头已打开，按 'q' 退出\n")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            detections = detector.detect_from_frame(frame)
            
            for det in detections:
                x, y = det.position
                cv2.circle(frame, (int(x), int(y)), 5, (0, 255, 0), -1)
                cv2.putText(frame, f"{det.weed_type}:{det.confidence:.1%}", 
                           (int(x)+10, int(y)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow('RayMind AI Detection', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
    except ImportError:
        print("需要安装 opencv-python: pip install opencv-python")
        demo_ai_module()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--camera':
        demo_with_camera()
    else:
        demo_ai_module()
