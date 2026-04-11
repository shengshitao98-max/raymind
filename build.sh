#!/bin/bash
# RayMind OS 打包脚本

echo "
╔══════════════════════════════════════════════════════════════════╗
║               RayMind 智能农田机器人 - 打包工具                ║
╚══════════════════════════════════════════════════════════════════╝
"

# 检查PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "[1/5] 安装 PyInstaller..."
    pip3 install pyinstaller
fi

echo "[2/5] 检查依赖..."
pip3 install PyQt5

echo "[3/5] 创建打包配置..."
cat > raymind.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['raymind/gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('raymind/*.md', 'raymind'),
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
    [],
    exclude_binaries=True,
    name='RayMind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RayMind',
)
EOF

echo "[4/5] 开始打包 (这可能需要几分钟)..."
pyinstaller raymind.spec --clean --noconfirm

echo "[5/5] 清理临时文件..."
rm -rf build/ raymind.spec __pycache__ raymind/__pycache__

echo "
╔══════════════════════════════════════════════════════════════════╗
║                       打包完成!                              ║
╠══════════════════════════════════════════════════════════════════╣
║  可执行文件位置:                                             ║
║  dist/RayMind/RayMind (Linux)                               ║
║  dist/RayMind.exe (Windows)                                 ║
║                                                              ║
║  运行: ./dist/RayMind/RayMind                               ║
╚══════════════════════════════════════════════════════════════════╝
"
