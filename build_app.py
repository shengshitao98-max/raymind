#!/usr/bin/env python3
"""
RayMind OS - 打包脚本
使用 PyInstaller 将Qt界面打包为可执行文件
"""

import os
import sys
import shutil

def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    print("正在安装 PyInstaller...")
    os.system("pip3 install pyinstaller")
    return check_pyinstaller()

def create_spec_file():
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['raymind/qt_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('raymind/templates', 'raymind/templates'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui', 
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RayMind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='raymind/templates/icon.ico' if os.path.exists('raymind/templates/icon.ico') else None,
)
'''
    with open('RayMind.spec', 'w') as f:
        f.write(spec_content)
    print("已创建 RayMind.spec")

def build_app():
    print("""
╔══════════════════════════════════════════════════════════════╗
║            RayMind OS - 打包工具                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    if not check_pyinstaller():
        if not install_pyinstaller():
            print("❌ 无法安装 PyInstaller，请手动安装: pip3 install pyinstaller")
            return
    
    print("[1/3] 创建配置文件...")
    create_spec_file()
    
    print("[2/3] 开始打包...")
    print("      (这可能需要几分钟...)")
    
    os.system("pyinstaller RayMind.spec --clean --noconfirm")
    
    print("[3/3] 清理临时文件...")
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('RayMind.spec'):
        os.remove('RayMind.spec')
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    打包完成!                                ║
╠══════════════════════════════════════════════════════════════╣
║  可执行文件位置: dist/RayMind                               ║
║                                                              ║
║  运行: ./dist/RayMind                                       ║
╚══════════════════════════════════════════════════════════════╝
    """)

def build_macos_app():
    print("正在打包 macOS 应用...")
    os.system("pyinstaller raymind/qt_gui.py "
              "--name RayMind "
              "--onedir "
              "--windowed "
              "--clean")
    print("打包完成! 应用位置: dist/RayMind.app")

def build_linux_app():
    print("正在打包 Linux 应用...")
    os.system("pyinstaller raymind/qt_gui.py "
              "--name RayMind "
              "--onedir "
              "--windowed "
              "--clean")
    print("打包完成! 应用位置: dist/RayMind")

if __name__ == '__main__':
    if sys.platform == 'darwin':
        build_macos_app()
    elif sys.platform.startswith('linux'):
        build_linux_app()
    else:
        build_app()
