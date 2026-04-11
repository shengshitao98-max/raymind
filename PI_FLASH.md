# RayMind 树莓派烧录指南

## 硬件要求

| 组件 | 型号 | 说明 |
|------|------|------|
| 开发板 | Raspberry Pi 5 8GB | 或 Jetson Nano |
| 存储 | 64GB+ TF卡 | 建议 Samsung EVO |
| 电源 | 5V 3A | 官方电源 |

---

## 方式一：使用 Raspberry Pi Imager（推荐）

### 1. 下载工具

```bash
# Ubuntu
sudo apt install rpi-imager

# 或从官网下载
# https://www.raspberrypi.com/software/
```

### 2. 烧录系统

1. 打开 Raspberry Pi Imager
2. 选择操作系统 → Other general purpose → Ubuntu Server 22.04
3. 选择TF卡
4. 点击烧录

### 3. 配置SSH

```bash
# 烧录后，在boot分区创建空文件
touch /media/$USER/boot/ssh

# 创建WiFi配置
cat > /media/$USER/boot/wpa_supplicant.conf <<EOF
country=CN
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={
    ssid="你的WiFi名称"
    psk="你的WiFi密码"
}
EOF
```

---

## 方式二：命令行烧录

### 1. 下载镜像

```bash
# Raspberry Pi OS
wget https://downloads.raspberrypi.org/raspios_lite_arm64/images/raspios_lite_arm64-2024-03-15/2024-03-15-raspios-lite-arm64.img.xz

# 或 Ubuntu
wget https://cdimage.ubuntu.com/releases/22.04.3/release/ubuntu-22.04.3-preinstalled-server-arm64+raspi.img.xz
```

### 2. 烧录到TF卡

```bash
# 查看设备名
sudo fdisk -l

# 假设设备为 /dev/mmcblk0
xz -d *.img.xz
sudo dd if=*.img of=/dev/mmcblk0 bs=4M status=progress
sync
```

---

## 方式三：Jetson Nano 烧录

### 1. 下载SDK Manager

```bash
# 从NVIDIA官网下载
# https://developer.nvidia.com/jetson-download-center
```

### 2. 进入恢复模式

1. 用USB线连接 Jetson Nano 到电脑
2. 按住强制恢复按钮
3. 按一下电源按钮
4. 释放强制恢复按钮

### 3. 烧录

```bash
# 打开SDK Manager
sdkmanager

# 选择 Jetson Nano 4GB/8GB
# 烧录 Ubuntu + ROS2
```

---

## 首次启动配置

### 1. SSH连接

```bash
# 查找IP
sudo nmap -sP 192.168.1.0/24

# SSH连接
ssh ubuntu@192.168.1.x
# 密码: ubuntu
```

### 2. 基础配置

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 设置时区
sudo timedatectl set-timezone Asia/Shanghai

# 改密码
passwd
```

### 3. 安装RayMind

```bash
# 克隆项目
git clone https://github.com/shengshitao98-max/raymind.git
cd raymind

# 安装
chmod +x install.sh
./install.sh
```

---

## Docker部署（如需要）

```bash
# 拉取镜像
docker pull raymind/robot:latest

# 运行
docker run -it --privileged --network host raymind/robot
```

---

## 快速启动

```bash
# 启动ROS2
source /opt/ros/humble/setup.bash
ros2 launch raymind_robot robot.launch.py

# 或启动GUI
python3 raymind/gui.py
```

---

## 注意事项

1. **散热**：Jetson Nano 需要外接风扇
2. **电源**：使用5V 3A电源，避免供电不足
3. **网络**：建议使用有线网络更稳定
4. **存储**：使用高速TF卡（U3级别）

---

*文档版本: 1.0*
