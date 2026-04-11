# RayMind 树莓派烧录指南

## 硬件要求

| 组件 | 型号 | 说明 |
|------|------|------|
| 开发板 | **Raspberry Pi 4B 8GB** | 推荐 |
| 存储 | 64GB+ TF卡 | 建议 Samsung EVO |
| 电源 | 5V 3A | 官方电源 |

---

## Windows 烧录方法

### 方式一：Raspberry Pi Imager（推荐）

#### 1. 下载工具

访问官网下载：
https://www.raspberrypi.com/software/

或直接下载：
- [Raspberry Pi Imager for Windows](https://downloads.raspberrypi.org/imager/imager_latest.exe)

#### 2. 烧录步骤

1. 插入TF卡到电脑
2. 打开 Raspberry Pi Imager
3. 选择操作系统：
   - **Raspberry Pi OS (Other)** → **Raspberry Pi OS Lite (64-bit)**
   - 或 **Ubuntu** → **Ubuntu Server 22.04 (64-bit)**
4. 选择TF卡
5. 点击**齿轮图标**进行高级设置：
   - ✅ 启用SSH
   - ✅ 设置用户名密码
   - ✅ 配置WiFi
6. 点击**烧录**

---

### 方式二：Jetson Nano 烧录

#### 1. 下载SDK Manager

访问：https://developer.nvidia.com/jetson-download-center

下载 **NVIDIA SDK Manager** for Windows

#### 2. 进入恢复模式

1. 用USB线连接 Jetson Nano 到电脑
2. **按住**强制恢复按钮（Force Recovery）
3. **按一下**电源按钮
4. **松开**强制恢复按钮

电脑设备管理器会出现**NVIDIA APX**设备

#### 3. 烧录

1. 打开 SDK Manager
2. 登录NVIDIA账户
3. 选择 **Jetson Nano**
4. 选择 **JetPack 5.x**（推荐）
5. 点击 **Install**

---

## Ubuntu/Linux 烧录方法

### 方式一：使用 Raspberry Pi Imager

```bash
# 安装
sudo apt install rpi-imager

# 打开
rpi-imager
```

### 方式二：命令行烧录

```bash
# 下载镜像
wget https://cdimage.ubuntu.com/releases/22.04.3/release/ubuntu-22.04.3-preinstalled-server-arm64+raspi.img.xz

# 查看设备
sudo fdisk -l

# 烧录（假设设备为 /dev/mmcblk0）
xz -d *.img.xz
sudo dd if=ubuntu-22.04.3-preinstalled-server-arm64+raspi.img of=/dev/mmcblk0 bs=4M status=progress
sync
```

---

## 首次启动配置

### 1. SSH连接

```bash
# 查找IP（路由器后台或使用工具）
# Advanced IP Scanner: https://advanced-ip-scanner.com/

# SSH连接
ssh ubuntu@192.168.1.x
# 密码: 你设置的密码
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

1. **散热**：需要外接散热片或风扇
2. **电源**：使用5V 3A电源，避免供电不足
3. **网络**：建议使用有线网络更稳定
4. **存储**：使用高速TF卡（U3级别）
5. **系统建议**：Ubuntu Server 22.04 或 Raspberry Pi OS

---

## Windows 常用工具

| 工具 | 用途 | 下载 |
|------|------|------|
| Raspberry Pi Imager | 烧录系统 | raspberrypi.com/software |
| NVIDIA SDK Manager | Jetson烧录 | developer.nvidia.com |
| PuTTY | SSH连接 | putty.org |
| Advanced IP Scanner | 查找IP | advanced-ip-scanner.com |
| Win32 Disk Imager | 备份镜像 | sourceforge.net/projects/win32diskimager |

---

*文档版本: 1.1*
