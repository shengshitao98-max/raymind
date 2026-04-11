# RayMind Robot Docker Image
# Build: docker build -t raymind/robot .
# Run:   docker run -it --privileged --network host raymind/robot

FROM ubuntu:22.04

LABEL maintainer="RayMind <raymind@robot.com>"
LABEL description="RayMind Smart Farm Robot Control System"

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install base dependencies
RUN apt-get update && apt-get install -y \
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
    udev \
    gnupg2 \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install ROS2 Humble
RUN apt-get update && apt-get install -y \
    locales \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=en_US.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -s https://packages.ros.org/ros.key | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://packages.ros.org/ros/ubuntu jammy main" > /etc/apt/sources.list.d/ros.list' \
    && apt-get update \
    && apt-get install -y \
    ros-humble-ros-base \
    ros-humble-demo-nodes-cpp \
    ros-humble-demo-nodes-py \
    ros-humble-teleop-twist-keyboard \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    ros-humble-xacro \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    PyQt5 \
    numpy \
    opencv-python \
    pyyaml \
    pyserial \
    smbus2 \
    pillow \
    flask \
    requests

# Install ROS2 Python packages
RUN pip3 install --no-cache-dir \
    rclpy \
    std_msgs \
    geometry_msgs \
    sensor_msgs \
    nav_msgs \
    vision_msgs \
    image_transport \
    cv_bridge \
    transforms3d

# Create workspace
WORKDIR /root
RUN mkdir -p /root/raymind /root/ros2_ws/src

# Copy source files
COPY raymind/ /root/raymind/
COPY ros2_ws/src/ /root/ros2_ws/src/

# Build ROS2 workspace
RUN . /opt/ros/humble/setup.sh && \
    cd /root/ros2_ws && \
    colcon build --symlink-install || true

# Setup environment
RUN echo "source /opt/ros/humble/setup.sh" >> /root/.bashrc && \
    echo "source /root/ros2_ws/install/setup.sh" >> /root/.bashrc && \
    echo "export RAYMIND_DIR=/root/raymind" >> /root/.bashrc && \
    echo "export ROS_DOMAIN_ID=42" >> /root/.bashrc && \
    echo "alias raymind-gui='python3 \$RAYMIND_DIR/gui.py'" >> /root/.bashrc

WORKDIR /root

CMD ["/bin/bash"]
