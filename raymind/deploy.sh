#!/bin/bash
# Farm Robot OS - 硬件部署脚本
# 在树莓派上运行此脚本进行安装

set -e

echo "=========================================="
echo "  智能农田作业机器人 - 硬件部署脚本"
echo "=========================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

echo "[1/6] 更新系统..."
apt update && apt upgrade -y

echo "[2/6] 安装系统依赖..."
apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    vim \
    htop \
    i2c-tools \
    python3-serial \
    python3-rpi.gpio

echo "[3/6] 启用I2C和SPI接口..."
if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" >> /etc/modules
fi
if ! grep -q "spi-dev" /etc/modules; then
    echo "spi-dev" >> /etc/modules
fi

# 启用I2C和SPI（需要重启）
raspi-config nonint do_i2c 0
raspi-config nonint do_spi 0

echo "[4/6] 安装Python依赖..."
pip3 install --upgrade pip
pip3 install \
    numpy \
    opencv-python \
    smbus \
    spidev \
    RPi.GPIO \
    pyserial \
    flask

echo "[5/6] 克隆或复制项目..."
if [ -d "/home/pi/farm_robot" ]; then
    cd /home/pi/farm_robot
    git pull
else
    mkdir -p /home/pi
    # 如果有远程仓库
    # git clone https://github.com/your-repo/farm_robot.git /home/pi/farm_robot
fi

echo "[6/6] 创建服务..."
cat > /etc/systemd/system/farmrobot.service << 'EOF'
[Unit]
Description=Farm Robot OS Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/farm_robot
ExecStart=/usr/bin/python3 /home/pi/farm_robot/farm_robot_os/web_gui.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable farmrobot

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
echo ""
echo "下一步操作:"
echo "1. 重启系统: sudo reboot"
echo "2. 连接硬件传感器"
echo "3. 启动服务: sudo systemctl start farmrobot"
echo "4. 查看状态: sudo systemctl status farmrobot"
echo "5. 访问控制台: http://树莓派IP:8080"
echo ""
