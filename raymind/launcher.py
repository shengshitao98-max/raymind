#!/usr/bin/env python3
"""
RayMind OS - 统一启动器
"""
import sys
import os

def check_pyqt5():
    try:
        from PyQt5.QtWidgets import QApplication
        return True
    except ImportError:
        return False

def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                    🌾 RayMind 智能农田机器人                     ║
║                         统一控制台 v1.0                       ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  请选择运行模式:                                                ║
║                                                                  ║
║  [1] 🖥️ 整合版 (推荐)  - 状态监控+控制+日志                    ║
║  [2] 🌐 Web控制台     - 浏览器访问，适合远程控制                ║
║  [3] ❌ 退出                                                      ║
║                                                                  ╚══════════════════════════════════════════════════════════════════╝
    """)
    
    choice = input("请输入选项 (1-3): ").strip()
    
    if choice == '1':
        if not check_pyqt5():
            print("\n❌ PyQt5未安装")
            print("安装命令: pip3 install PyQt5\n")
            ans = input("是否现在安装? (y/n): ").strip().lower()
            if ans == 'y':
                os.system("pip3 install PyQt5")
            else:
                return
        print("\n启动整合版控制台...\n")
        os.system("python3 raymind/gui.py")
    
    elif choice == '2':
        print("\n启动Web控制台...")
        print("访问地址: http://localhost:8080\n")
        os.system("python3 raymind/web_gui.py")
    
    elif choice == '3':
        print("\n再见!\n")
        sys.exit(0)
    
    else:
        print("\n无效选项\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
