# RayMind Robot Docker Image

FROM ros:humble-ros-base-jammy

LABEL maintainer="RayMind <raymind@robot.com>"
LABEL description="RayMind Smart Farm Robot Control System"

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble

WORKDIR /root

RUN apt-get update && apt-get install -y --no-install-recommends \
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
    ros-humble-desktop \
    ros-humble-teleop-twist-keyboard \
    ros-humble-robot-state-publisher \
    ros-humble-joint-state-publisher \
    ros-humble-realsense2-camera \
    ros-humble-navigation2 \
    ros-humble-slam-toolbox \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    PyQt5 \
    numpy \
    opencv-python \
    pyyaml \
    pyserial \
    smbus2

COPY raymind/ /root/raymind/
COPY ros2_ws/ /root/ros2_ws/

RUN cd /root/ros2_ws && \
    source /opt/ros/humble/setup.bash && \
    colcon build || true

RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo "source /root/ros2_ws/install/setup.bash" >> /root/.bashrc && \
    echo "export RAYMIND_DIR=/root/raymind" >> /root/.bashrc && \
    echo "export ROS_DOMAIN_ID=42" >> /root/.bashrc

CMD ["bash"]
