"""
RayMind OS
智能农田作业机器人操作系统
"""

from .core import (
    EventBus, Event, EventType,
    StateMachine, RobotState,
    RobotStatusManager, RobotStatus, Position, TargetInfo
)

from .sensors import (
    SensorManager, DepthCameraSensor, LidarSensor, GPSSensor, IMUSensor,
    DepthImageData, LidarScanData, GPSData, IMUData
)

from .motion import (
    MotionManager, MotionConfig, Pose, VelocityCommand,
    MotorController, NavigationController, LaserController
)

from .scheduler import (
    TaskScheduler, TaskPriority, TaskStatus, MissionPlanner
)

from .controller import FarmRobotController, RobotAPI

__all__ = [
    "EventBus", "Event", "EventType",
    "StateMachine", "RobotState",
    "RobotStatusManager", "RobotStatus", "Position", "TargetInfo",
    "SensorManager", "DepthCameraSensor", "LidarSensor", "GPSSensor", "IMUSensor",
    "DepthImageData", "LidarScanData", "GPSData", "IMUData",
    "MotionManager", "MotionConfig", "Pose", "VelocityCommand",
    "MotorController", "NavigationController", "LaserController",
    "TaskScheduler", "TaskPriority", "TaskStatus", "MissionPlanner",
    "FarmRobotController", "RobotAPI"
]

__version__ = "1.0.0"
__name__ = "RayMind"
