# RayMind 智能农田机器人 - 完整操作手册

## 目录

1. [快速开始](#1-快速开始)
2. [硬件清单](#2-硬件清单)
3. [硬件组装](#3-硬件组装)
4. [Docker部署](#4-docker部署)
5. [本地安装](#5-本地安装)
6. [机器人端配置](#6-机器人端配置)
7. [控制端配置](#7-控制端配置)
8. [使用方法](#8-使用方法)
9. [故障排除](#9-故障排除)

---

## 1. 快速开始

### 方式一：Docker部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/shengshitao98-max/raymind.git
cd raymind

# 2. 构建Docker镜像
docker build -t raymind/robot .

# 3. 运行容器
# 机器人端
docker run -it --privileged --network host raymind/robot

# 4. 启动ROS2
ros2 launch raymind_robot robot.launch.py
```

### 方式二：本地安装

```bash
# 使用安装脚本
chmod +x install.sh
./install.sh

# 启动GUI
python3 raymind/gui.py
```

---

## 2. 硬件清单

### 核心部件

| 部件 | 型号 | 数量 | 接口 |
|------|------|------|------|
| 主控计算机 | Jetson Orin Nano 8GB | 1 | - |
| 激光雷达 | YDLIDAR X4 | 1 | USB |
| 深度相机 | RealSense D435i | 1 | USB |
| IMU | ICM-20948 | 1 | I2C |
| GPS | NEO-7M | 1 | UART |
| 电机驱动 | BTS7960 | 1 | GPIO |
| 履带底盘 | 30kg承重 | 1 | - |
| 锂电池 | 48V 15Ah | 1 | - |

### 通信模块

| 模块 | 型号 | 用途 |
|------|------|------|
| WiFi网卡 | Intel AX210 | 无线控制 |
| 蓝牙适配器 | BT 5.0 | 近距离遥控 |

---

## 3. 硬件组装

### 3.1 接口连线图

```
Jetson Orin Nano 40-pin GPIO
────────────────────────────────────────────────────────────

  1  3.3V   2  5V         ← 电源输出
  3  GPIO2   4  5V
  5  GPIO3   6  GND
  7  GPIO4   8  GPIO14    ← 电机A方向
  9  GND    10  GPIO15
 11 GPIO17  12  GPIO18    ← 电机B方向
 13 GPIO27  14  GND
 15 GPIO22  16  GPIO23
 17 3.3V   18  GPIO24
 19 GPIO10  20  GND       ← GND
 21  GPIO9  22  GPIO25
 23  GPIO11 24  GPIO8
 25  GND    26  GPIO7
 27  ID_SD  28  ID_SC     ← I2C (IMU)
 29  GPIO5  30  GND
 31  GPIO6  32  GPIO12    ← 电机A使能(PWM)
 33  GPIO13 34  GND
 35  GPIO19 36  GPIO16    ← 电机B使能(PWM)
 37  GPIO26 38  GPIO20
 39  GND    40  GPIO21
```

### 3.2 传感器连接

| 传感器 | 接口 | 线序 |
|--------|------|------|
| 激光雷达 | USB | 直接连接 |
| 深度相机 | USB | 直接连接 |
| IMU | I2C | SDA→SDA, SCL→SCL, VCC→3.3V, GND→GND |
| GPS | UART | TX→RX, RX→TX, VCC→5V, GND→GND |
| 电机驱动 | GPIO | 见上方GPIO表 |

### 3.3 电源连接

```
48V锂电池
    │
    ├──→ DC-DC 48V→12V ──→ Jetson (12V)
    │
    ├──→ DC-DC 48V→5V ──→ 激光雷达 (5V)
    │                      相机 (5V)
    │                      GPS (5V)
    │
    └──→ 电机驱动 (48V) ──→ 履带电机
```

---

## 4. Docker部署

### 4.1 构建镜像

```bash
# 克隆项目
git clone https://github.com/shengshitao98-max/raymind.git
cd raymind

# 构建
docker build -t raymind/robot:latest .
```

### 4.2 运行容器

```bash
# 机器人端 - 需要硬件访问权限
docker run -it --privileged \
    --network host \
    --device /dev/ttyUSB0:/dev/ttyUSB0 \
    --device /dev/video0:/dev/video0 \
    -v /dev/bus/usb:/dev/bus/usb \
    raymind/robot:latest

# 控制端 - 无需硬件
docker run -it --network host raymind/robot:latest
```

### 4.3 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  robot:
    image: raymind/robot:latest
    container_name: raymind_robot
    privileged: true
    network_mode: host
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/video0:/dev/video0
    volumes:
      - ./ros2_ws:/root/ros2_ws
    environment:
      - ROS_DOMAIN_ID=42

  gui:
    image: raymind/robot:latest
    container_name: raymind_gui
    network_mode: host
    environment:
      - DISPLAY=${DISPLAY}
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
    command: python3 raymind/gui.py
```

---

## 5. 本地安装

### 5.1 系统要求

- Ubuntu 22.04 LTS
- ROS2 Humble
- Python 3.10+

### 5.2 安装脚本

```bash
# 自动安装
chmod +x install.sh
./install.sh

# 或手动安装
sudo apt update
sudo apt install -y python3-pip ros-humble-desktop

pip3 install PyQt5 numpy opencv-python rclpy
```

### 5.3 ROS2工作空间

```bash
cd ~/raymind/ros2_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

---

## 6. 机器人端配置

### 6.1 启动ROS2

```bash
# SSH到机器人
ssh jetson@192.168.1.100

# 启动ROS2
cd ~/raymind/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch raymind_robot robot.launch.py
```

### 6.2 启动各传感器

```bash
# 启动相机
ros2 launch realsense2_camera rs_launch.py

# 启动激光雷达
ros2 launch ydlidar_ros2_driver ydlidar.launch.py
```

---

## 7. 控制端配置

### 7.1 同一局域网

```
控制电脑 ──WiFi── 路由器 ──WiFi── 机器人
```

```bash
# 控制端 - 设置网络
export ROS_DOMAIN_ID=42

# 验证连接
ros2 topic list
```

### 7.2 启动GUI

```bash
# 控制端
cd ~/raymind
python3 raymind/gui.py
```

---

## 8. 使用方法

### 8.1 GUI操作

1. **启动GUI**
   ```bash
   python3 raymind/gui.py
   ```

2. **连接机器人**
   - 点击"🔗 连接ROS2"按钮
   - 等待状态变为"🟢 在线"

3. **控制机器人**
   - 使用方向键控制移动
   - 观察状态栏实时数据

### 8.2 键盘控制

```bash
# 启动键盘控制
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 按键说明:
# i = 前进
# , = 后退
# j = 左转
# l = 右转
# k = 停止
```

---

## 9. 故障排除

### 9.1 无法连接ROS2

```bash
# 检查网络
ping 192.168.1.100

# 检查ROS_DOMAIN_ID
echo $ROS_DOMAIN_ID

# 检查话题
ros2 topic list
```

### 9.2 传感器无数据

```bash
# 检查USB设备
lsusb

# 检查驱动
dmesg | grep ttyUSB
```

### 9.3 电机不动

```bash
# 检查GPIO权限
sudo usermod -a -G gpio $USER
logout

# 检查权限
ls -la /dev/gpio*
```

---

## 快速启动命令

### 机器人端（Docker）
```bash
docker run -it --privileged --network host raymind/robot:latest
ros2 launch raymind_robot robot.launch.py
```

### 机器人端（本地）
```bash
ssh jetson@192.168.1.100
cd ~/raymind/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch raymind_robot robot.launch.py
```

### 控制端
```bash
export ROS_DOMAIN_ID=42
cd ~/raymind
python3 raymind/gui.py
```

---

*文档版本: 1.1*
*更新日期: 2025*
