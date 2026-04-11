#!/usr/bin/env python3
"""
RayMind OS - 快速打包工具
"""
import os
import sys
import subprocess
import shutil

def build():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║               RayMind 智能农田机器人 - 打包工具              ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # 检查并安装依赖
    print("[1/4] 检查依赖...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller 已安装")
    except ImportError:
        print("  安装 PyInstaller...")
        os.system("pip3 install pyinstaller")
        try:
            import PyInstaller
            print("  ✓ PyInstaller 安装成功")
        except:
            print("  ✗ PyInstaller 安装失败，请手动运行: pip3 install pyinstaller")
            return

    print("[2/4] 打包应用程序...")

    # 使用 python -m pyinstaller 确保能找到
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=RayMind",
        "--windowed",
        "--onedir",
        "--clean",
        "--noconfirm",
        "--add-data=raymind:raymind",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "raymind/gui.py"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        if result.returncode != 0:
            print(f"  打包失败: {result.stderr}")
            # 尝试备用方案
            print("  尝试备用方案...")
            backup_cmd = [
                "pyinstaller",
                "--name=RayMind",
                "--windowed",
                "--onedir",
                "--clean",
                "raymind/gui.py"
            ]
            result = subprocess.run(backup_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  备用方案也失败: {result.stderr}")
                return
    except Exception as e:
        print(f"  执行错误: {e}")
        return

    print("[3/4] 复制必要文件...")

    dist_dir = "dist/RayMind"

    # 复制模型文件
    if os.path.exists("best.pt"):
        try:
            shutil.copy("best.pt", dist_dir + "/")
            print("  ✓ 复制 best.pt")
        except:
            pass

    # 复制文档
    if os.path.exists("raymind/HARDWARE.md"):
        try:
            os.makedirs(dist_dir + "/raymind", exist_ok=True)
            shutil.copy("raymind/HARDWARE.md", dist_dir + "/raymind/")
            print("  ✓ 复制 HARDWARE.md")
        except:
            pass

    print("[4/4] 完成!")

    print("""
╔══════════════════════════════════════════════════════════════════╗
║                       打包完成!                              ║
╠══════════════════════════════════════════════════════════════════╣
║                                                              ║
║  Linux:   ./dist/RayMind/RayMind                          ║
║  Windows: .\\dist\\RayMind\\RayMind.exe                  ║
║  macOS:   ./dist/RayMind.app                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == '__main__':
    build()
