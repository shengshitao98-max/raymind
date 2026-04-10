#!/usr/bin/env python3
"""
ROS2 集成模块 - RayMind Robot Control
支持 ROS2 Humble/Iron/Jazzy
"""

import os
import sys
import logging
import threading
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

ROS2_AVAILABLE = False

try:
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
    from sensor_msgs.msg import Image, LaserScan, NavSatFix, Imu
    from geometry_msgs.msg import Twist, Pose
    from nav_msgs.msg import Odometry
    from std_msgs.msg import String, Bool, Float32
    ROS2_AVAILABLE = True
except ImportError:
    logger.warning("ROS2 not installed. Run: pip install rclpy")
    Node = object


class ROS2Interface(Node):
    """ROS2 通信接口"""
    
    def __init__(self, node_name: str = "raymind_node"):
        if not ROS2_AVAILABLE:
            raise RuntimeError("ROS2 not available")
        
        super().__init__(node_name)
        
        self.cmd_vel_pub = None
        self.laser_sub = None
        self.odom_sub = None
        self.gps_sub = None
        self.imu_sub = None
        self.camera_sub = None
        
        self.latest_scan = None
        self.latest_odom = None
        self.latest_gps = None
        self.latest_imu = None
        self.latest_image = None
        
        self._initialized = False
        self._spin_thread = None
        self._running = False
    
    def initialize_publishers(self):
        """初始化发布者"""
        self.cmd_vel_pub = self.create_publisher(
            Twist, '/cmd_vel', 10
        )
        
        self.status_pub = self.create_publisher(
            String, '/raymind/status', 10
        )
        
        self.get_logger().info("ROS2 publishers initialized")
        self._initialized = True
    
    def initialize_subscribers(self):
        """初始化订阅者"""
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        self.laser_sub = self.create_subscription(
            LaserScan, '/scan', self._scan_callback, qos
        )
        
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self._odom_callback, qos
        )
        
        self.gps_sub = self.create_subscription(
            NavSatFix, '/gps/fix', self._gps_callback, qos
        )
        
        self.imu_sub = self.create_subscription(
            Imu, '/imu/data', self._imu_callback, qos
        )
        
        self.camera_sub = self.create_subscription(
            Image, '/camera/image_raw', self._camera_callback, qos
        )
        
        self.get_logger().info("ROS2 subscribers initialized")
    
    def _scan_callback(self, msg: LaserScan):
        self.latest_scan = msg
    
    def _odom_callback(self, msg: Odometry):
        self.latest_odom = msg
    
    def _gps_callback(self, msg: NavSatFix):
        self.latest_gps = msg
    
    def _imu_callback(self, msg: Imu):
        self.latest_imu = msg
    
    def _camera_callback(self, msg: Image):
        self.latest_image = msg
    
    def publish_cmd_vel(self, linear_x: float = 0.0, linear_y: float = 0.0,
                       linear_z: float = 0.0, angular_x: float = 0.0,
                       angular_y: float = 0.0, angular_z: float = 0.0):
        """发布速度命令"""
        if self.cmd_vel_pub is None:
            return
        
        msg = Twist()
        msg.linear.x = linear_x
        msg.linear.y = linear_y
        msg.linear.z = linear_z
        msg.angular.x = angular_x
        msg.angular.y = angular_y
        msg.angular.z = angular_z
        self.cmd_vel_pub.publish(msg)
    
    def move_forward(self, speed: float = 0.5):
        self.publish_cmd_vel(linear_x=speed)
    
    def move_backward(self, speed: float = 0.5):
        self.publish_cmd_vel(linear_x=-speed)
    
    def turn_left(self, speed: float = 0.5):
        self.publish_cmd_vel(angular_z=speed)
    
    def turn_right(self, speed: float = 0.5):
        self.publish_cmd_vel(angular_z=-speed)
    
    def stop(self):
        self.publish_cmd_vel(0, 0, 0, 0, 0, 0)
    
    def get_laser_scan(self) -> Optional[LaserScan]:
        return self.latest_scan
    
    def get_odometry(self) -> Optional[Odometry]:
        return self.latest_odom
    
    def get_gps(self) -> Optional[NavSatFix]:
        return self.latest_gps
    
    def get_imu(self) -> Optional[Imu]:
        return self.latest_imu
    
    def get_camera_frame(self) -> Optional[Image]:
        return self.latest_image
    
    def start_spinning(self):
        """开始spin线程"""
        if self._running:
            return
        
        self._running = True
        self._spin_thread = threading.Thread(target=self._spin_loop, daemon=True)
        self._spin_thread.start()
        logger.info("ROS2 spinning started")
    
    def _spin_loop(self):
        while self._running and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.1)
    
    def stop_spinning(self):
        """停止spin线程"""
        self._running = False
        if self._spin_thread:
            self._spin_thread.join(timeout=1.0)
        logger.info("ROS2 spinning stopped")
    
    def shutdown(self):
        """关闭节点"""
        self.stop_spinning()
        self.destroy_node()
        logger.info("ROS2 node shutdown")


class ROS2Manager:
    """ROS2 管理器"""
    
    def __init__(self, node_name: str = "raymind"):
        self.node = None
        self.node_name = node_name
        self.ros_interface = None
        self._ros_thread = None
        self._running = False
    
    def start(self) -> bool:
        """启动ROS2"""
        if not ROS2_AVAILABLE:
            logger.error("ROS2 not installed")
            return False
        
        try:
            rclpy.init()
            self.ros_interface = ROS2Interface(self.node_name)
            self.ros_interface.initialize_publishers()
            self.ros_interface.initialize_subscribers()
            self.ros_interface.start_spinning()
            self._running = True
            logger.info(f"ROS2 started: {self.node_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start ROS2: {e}")
            return False
    
    def stop(self):
        """停止ROS2"""
        self._running = False
        if self.ros_interface:
            self.ros_interface.shutdown()
        if rclpy.ok():
            rclpy.shutdown()
        logger.info("ROS2 stopped")
    
    def is_running(self) -> bool:
        return self._running and self.ros_interface is not None
    
    def move_robot(self, linear: float = 0.0, angular: float = 0.0):
        """控制机器人移动"""
        if self.ros_interface:
            self.ros_interface.publish_cmd_vel(linear_x=linear, angular_z=angular)
    
    def get_sensor_data(self) -> Dict:
        """获取传感器数据"""
        if not self.ros_interface:
            return {}
        
        data = {}
        
        scan = self.ros_interface.get_laser_scan()
        if scan:
            data['laser'] = {
                'ranges': list(scan.ranges),
                'angle_min': scan.angle_min,
                'angle_max': scan.angle_max,
                'angle_increment': scan.angle_increment
            }
        
        odom = self.ros_interface.get_odometry()
        if odom:
            data['odom'] = {
                'position': {
                    'x': odom.pose.pose.position.x,
                    'y': odom.pose.pose.position.y
                },
                'orientation': {
                    'x': odom.pose.pose.orientation.x,
                    'y': odom.pose.pose.orientation.y,
                    'z': odom.pose.pose.orientation.z,
                    'w': odom.pose.pose.orientation.w
                },
                'velocity': {
                    'linear': odom.twist.twist.linear.x,
                    'angular': odom.twist.twist.angular.z
                }
            }
        
        gps = self.ros_interface.get_gps()
        if gps:
            data['gps'] = {
                'latitude': gps.latitude,
                'longitude': gps.longitude,
                'altitude': gps.altitude
            }
        
        imu = self.ros_interface.get_imu()
        if imu:
            data['imu'] = {
                'orientation': {
                    'x': imu.orientation.x,
                    'y': imu.orientation.y,
                    'z': imu.orientation.z,
                    'w': imu.orientation.w
                },
                'angular_velocity': {
                    'x': imu.angular_velocity.x,
                    'y': imu.angular_velocity.y,
                    'z': imu.angular_velocity.z
                },
                'linear_acceleration': {
                    'x': imu.linear_acceleration.x,
                    'y': imu.linear_acceleration.y,
                    'z': imu.linear_acceleration.z
                }
            }
        
        return data
    
    def publish_status(self, status: str):
        """发布状态消息"""
        if self.ros_interface:
            msg = String()
            msg.data = status
            self.ros_interface.status_pub.publish(msg)


def create_ros2_node(node_name: str = "raymind") -> Optional[ROS2Interface]:
    """创建ROS2节点（独立使用）"""
    if not ROS2_AVAILABLE:
        return None
    
    try:
        rclpy.init()
        node = ROS2Interface(node_name)
        node.initialize_publishers()
        node.initialize_subscribers()
        node.start_spinning()
        return node
    except Exception as e:
        logger.error(f"Failed to create ROS2 node: {e}")
        return None


if __name__ == '__main__':
    print("ROS2 Interface Module for RayMind")
    print(f"ROS2 Available: {ROS2_AVAILABLE}")
    
    if ROS2_AVAILABLE:
        print("\nUsage:")
        print("  from ros2_interface import ROS2Manager")
        print("  ")
        print("  manager = ROS2Manager('raymind')")
        print("  manager.start()")
        print("  manager.move_robot(linear=0.5, angular=0.3)")
    else:
        print("\nInstall ROS2: https://docs.ros.org/en/humble/Installation.html")
