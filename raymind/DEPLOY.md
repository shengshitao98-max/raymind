# Farm Robot OS Docker 部署

## 快速部署 (Docker Compose)

```bash
# 1. 克隆项目
git clone https://github.com/your-repo/farm-robot-os.git
cd farm-robot-os

# 2. 构建并运行
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问控制台
# http://localhost:8080
```

## Docker 配置

### Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    i2c-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 安装Python依赖
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    flask

# 暴露端口
EXPOSE 8080

# 启动应用
CMD ["python", "farm_robot_os/web_gui.py"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  farm-robot:
    build: .
    container_name: farm-robot-os
    ports:
      - "8080:8080"
    devices:
      - /dev/i2c-1:/dev/i2c-1
      - /dev/spidev0.0:/dev/spidev0.0
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - HARDWARE_TYPE=raspberry_pi
      - I2C_BUS=1
    restart: unless-stopped
    network_mode: host
```

## 硬件连接图

### 树莓派 4B 引脚分配

```
┌─────────────────────────────────────────────┐
│           树莓派 4B GPIO                    │
├─────────────────────────────────────────────┤
│  I2C (SDA=SDA, SCL=SCL) → 深度相机/IMU    │
│  GPIO 18 → 激光控制 (PWM)                   │
│  GPIO 23 → 电机方向控制1                   │
│  GPIO 24 → 电机方向控制2                   │
│  GPIO 25 → 电机PWM调速                     │
│  UART (TX/RX) → GPS模块                    │
│  SPI (MOSI/MISO/CLK) → 激光雷达            │
└─────────────────────────────────────────────┘
```

### 硬件清单

| 组件 | 型号 | 接口 | 功能 |
|------|------|------|------|
| 主控 | 树莓派 4B 4GB | - | 运行ROS系统 |
| 深度相机 | Intel RealSense D435i | USB3.0 | 环境感知/目标识别 |
| 激光雷达 | RPLIDAR A1M8 | UART | 避障/建图 |
| GPS | NEO-6M/7M | UART | 定位 |
| IMU | MPU6050 | I2C | 姿态检测 |
| 电机驱动 | L298N/PCA9685 | I2C/PWM | 运动控制 |
| 激光器 | 808nm 2W | GPIO | 杂草清除 |
| 电池 | 24V 10Ah LiPo | - | 供电 |

## 部署检查清单

- [ ] 树莓派系统烧录并配置WiFi
- [ ] 启用I2C、SPI、Camera接口
- [ ] 安装ROS2 Foxy桌面版
- [ ] 编译项目代码
- [ ] 连接所有传感器线缆
- [ ] 测试各传感器数据
- [ ] 校准IMU/相机
- [ ] 测试运动控制
- [ ] 测试激光发射
- [ ] 部署Web控制台
- [ ] 安全测试

## 故障排查

```bash
# 检查I2C设备
sudo i2cdetect -y 1

# 检查USB设备
lsusb

# 查看串口
dmesg | grep tty

# 测试GPIO
gpio -v

# 查看ROS话题
ros2 topic list

# 查看日志
journalctl -u farmrobot -f
```

## 安全警告

⚠️ **激光安全**: 2W 808nm激光对眼睛有害，操作时必须佩戴防护眼镜
⚠️ **电气安全**: 确保电池极性正确，防止短路
⚠️ **机械安全**: 测试时保持安全距离
