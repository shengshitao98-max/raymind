#!/bin/bash

set -e

echo "=========================================="
echo "  RayMind 机器人环境安装脚本"
echo "=========================================="

INSTALL_DIR="$HOME/raymind"
ROS_DISTRO="humble"

check_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "无法检测操作系统"
        exit 1
    fi
    
    if [ "$OS" != "ubuntu" ]; then
        echo "仅支持 Ubuntu 系统"
        exit 1
    fi
    
    echo "检测到: $PRETTY_NAME"
}

install_system_deps() {
    echo ""
    echo ">>> 安装系统依赖..."
    sudo apt update
    sudo apt install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        vim \
        build-essential \
        libssl-dev \
        libffi-dev \
        libusb-1.0-0 \
        udev
}

install_ros() {
    echo ""
    echo ">>> 检查 ROS2..."
    
    if command -v ros2 &> /dev/null; then
        echo "ROS2 已安装"
        return
    fi
    
    echo "安装 ROS2 $ROS_DISTRO..."
    
    sudo apt install -y software-properties-common
    sudo add-apt-repository universe
    sudo apt update
    
    sudo apt install -y ros-$ROS_DISTRO-desktop
    
    source /opt/ros/$ROS_DISTRO/setup.bash
    
    echo "ROS2 安装完成"
}

install_python_deps() {
    echo ""
    echo ">>> 安装 Python 依赖..."
    
    pip3 install --upgrade pip
    
    pip3 install \
        PyQt5 \
        numpy \
        opencv-python \
        pyyaml \
        pyserial \
        smbus2 \
        rclpy \
        std_msgs \
        geometry_msgs \
        sensor_msgs \
        nav_msgs \
        vision_msgs \
        image_transport \
        cv_bridge \
        transform\
        
    echo "Python 依赖安装完成"
}

install_robot_deps() {
    echo ""
    echo ">>> 安装机器人相关驱动..."
    
    sudo apt install -y \
        ros-$ROS_DISTRO-realsense2-camera \
        ros-$ROS_DISTRO-teleop-twist-keyboard \
        ros-$ROS_DISTRO-robot-state-publisher \
        ros-$ROS_DISTRO-joint-state-publisher
        
    echo "机器人驱动安装完成"
}

clone_project() {
    echo ""
    echo ">>> 克隆项目..."
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "项目已存在，更新中..."
        cd "$INSTALL_DIR"
        git pull
    else
        git clone https://github.com/shengshitao98-max/raymind.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    echo "项目克隆完成"
}

setup_ros2_ws() {
    echo ""
    echo ">>> 设置 ROS2 工作空间..."
    
    if [ ! -d "$INSTALL_DIR/ros2_ws" ]; then
        mkdir -p "$INSTALL_DIR/ros2_ws/src"
        cd "$INSTALL_DIR/ros2_ws"
        source /opt/ros/$ROS_DISTRO/setup.bash
        colcon build
    fi
    
    echo "ROS2 工作空间设置完成"
}

create_aliases() {
    echo ""
    echo ">>> 创建快捷命令..."
    
    SHELL_RC="$HOME/.bashrc"
    
    if ! grep -q "raymind" "$SHELL_RC"; then
        echo "" >> "$SHELL_RC"
        echo "# RayMind 机器人" >> "$SHELL_RC"
        echo "export RAYMIND_DIR=$INSTALL_DIR" >> "$SHELL_RC"
        echo "alias raymind-gui='cd \$RAYMIND_DIR && python3 raymind/gui.py'" >> "$SHELL_RC"
        echo "alias raymind-start='cd \$RAYMIND_DIR/ros2_ws && source install/setup.bash && ros2 launch raymind_robot robot.launch.py'" >> "$SHELL_RC"
        echo "alias raymind-test='cd \$RAYMIND_DIR/ros2_ws && source install/setup.bash && ros2 topic list'" >> "$SHELL_RC"
    fi
    
    echo "快捷命令创建完成"
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  安装完成！"
    echo "=========================================="
    echo ""
    echo "快捷命令:"
    echo "  raymind-gui      - 启动GUI控制界面"
    echo "  raymind-start    - 启动机器人节点"
    echo "  raymind-test     - 测试ROS2连接"
    echo ""
    echo "手动启动:"
    echo "  source /opt/ros/$ROS_DISTRO/setup.bash"
    echo "  cd $INSTALL_DIR"
    echo "  python3 raymind/gui.py"
    echo ""
}

main() {
    check_os
    install_system_deps
    install_ros
    install_python_deps
    install_robot_deps
    clone_project
    setup_ros2_ws
    create_aliases
    print_summary
}

main "$@"
