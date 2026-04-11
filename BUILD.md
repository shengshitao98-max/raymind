# RayMind OS 打包指南

## 安装打包工具

```bash
pip3 install pyinstaller
```

## 打包命令

### Linux
```bash
pyinstaller --name RayMind --windowed --onedir raymind/qt_gui.py
```
生成: `dist/RayMind/qt_gui`

### macOS
```bash
pyinstaller --name RayMind --windowed --onedir raymind/qt_gui.py
```
生成: `dist/RayMind.app`

### Windows
```bash
pyinstaller --name RayMind --windowed --onedir raymind/qt_gui.py
```
生成: `dist/RayMind/RayMind.exe`

## 一键打包脚本
```bash
python3 build_app.py
```

## 打包后运行
```bash
./dist/RayMind/qt_gui
```

## 注意事项
- 需要先安装 PyQt5
- 打包后体积约 50-100MB
- 可添加图标: `--icon=logo.ico`
