"""
智能农田作业机器人操作系统
融合环境深度感知、自主导航、高精度杂草识别与定位、激光精准打击
"""

import sys
import time
import threading
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
import json
import queue

logger = logging.getLogger("FarmRobotOS")


class RobotState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    NAVIGATING = "navigating"
    SCANNING = "scanning"
    IDENTIFYING = "identifying"
    TARGETING = "targeting"
    EXECUTING = "executing"
    EMERGENCY_STOP = "emergency_stop"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class TaskType(Enum):
    PATROL = "patrol"
    SCAN = "scan"
    IDENTIFY = "identify"
    ERADICATE = "eradicate"
    NAVIGATE = "navigate"
    CHARGE = "charge"


@dataclass
class Position:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    
    def distance_to(self, other: 'Position') -> float:
        return ((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2) ** 0.5
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z, "yaw": self.yaw}


@dataclass
class TargetInfo:
    position: Position
    confidence: float = 0.0
    target_type: str = "weed"
    bounding_box: tuple = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RobotStatus:
    state: RobotState = RobotState.IDLE
    position: Position = field(default_factory=Position)
    battery_level: float = 100.0
    speed: float = 0.0
    temperature: float = 25.0
    error_code: int = 0
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "position": self.position.to_dict(),
            "battery_level": self.battery_level,
            "speed": self.speed,
            "temperature": self.temperature,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat()
        }


class EventType(Enum):
    STATE_CHANGED = "state_changed"
    TARGET_DETECTED = "target_detected"
    NAVIGATION_COMPLETE = "navigation_complete"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    BATTERY_LOW = "battery_low"
    SENSOR_DATA = "sensor_data"


class Event:
    def __init__(self, event_type: EventType, data: Any = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = datetime.now()


class EventBus:
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(callback)
    
    def publish(self, event: Event):
        subscribers = []
        with self._lock:
            subscribers = list(self._subscribers.get(event.event_type, []))
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")


class StateMachine:
    def __init__(self, event_bus: EventBus):
        self._current_state = RobotState.IDLE
        self._event_bus = event_bus
        self._state_history: List[tuple] = []
        self._lock = threading.Lock()
        self._allowed_transitions = {
            RobotState.IDLE: [RobotState.INITIALIZING, RobotState.SHUTDOWN],
            RobotState.INITIALIZING: [RobotState.READY, RobotState.ERROR, RobotState.SHUTDOWN],
            RobotState.READY: [RobotState.NAVIGATING, RobotState.SCANNING, RobotState.IDENTIFYING, 
                             RobotState.EMERGENCY_STOP, RobotState.SHUTDOWN],
            RobotState.NAVIGATING: [RobotState.READY, RobotState.SCANNING, RobotState.IDENTIFYING,
                                   RobotState.EMERGENCY_STOP, RobotState.ERROR],
            RobotState.SCANNING: [RobotState.READY, RobotState.NAVIGATING, RobotState.IDENTIFYING,
                                 RobotState.EMERGENCY_STOP, RobotState.ERROR],
            RobotState.IDENTIFYING: [RobotState.READY, RobotState.TARGETING, RobotState.NAVIGATING,
                                    RobotState.EMERGENCY_STOP, RobotState.ERROR],
            RobotState.TARGETING: [RobotState.EXECUTING, RobotState.READY, RobotState.EMERGENCY_STOP, RobotState.ERROR],
            RobotState.EXECUTING: [RobotState.READY, RobotState.IDENTIFYING, RobotState.EMERGENCY_STOP, RobotState.ERROR],
            RobotState.EMERGENCY_STOP: [RobotState.READY, RobotState.ERROR],
            RobotState.ERROR: [RobotState.IDLE, RobotState.SHUTDOWN],
            RobotState.SHUTDOWN: []
        }
    
    @property
    def current_state(self) -> RobotState:
        with self._lock:
            return self._current_state
    
    def can_transition(self, new_state: RobotState) -> bool:
        with self._lock:
            return new_state in self._allowed_transitions.get(self._current_state, [])
    
    def transition_to(self, new_state: RobotState) -> bool:
        with self._lock:
            if not self.can_transition(new_state):
                logger.warning(f"Invalid state transition: {self._current_state} -> {new_state}")
                return False
            
            old_state = self._current_state
            self._current_state = new_state
            self._state_history.append((old_state, new_state, datetime.now()))
            
            self._event_bus.publish(Event(EventType.STATE_CHANGED, {
                "old_state": old_state.value,
                "new_state": new_state.value
            }))
            
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
            return True
    
    def get_state_history(self) -> List[Dict]:
        return [
            {"from": h[0].value, "to": h[1].value, "timestamp": h[2].isoformat()}
            for h in self._state_history
        ]


class RobotStatusManager:
    def __init__(self, event_bus: EventBus):
        self._status = RobotStatus()
        self._event_bus = event_bus
        self._lock = threading.Lock()
        self._status_history: List[RobotStatus] = []
        self._max_history = 1000
    
    @property
    def status(self) -> RobotStatus:
        with self._lock:
            return self._status
    
    def update_status(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._status, key):
                    setattr(self._status, key, value)
            self._status.timestamp = datetime.now()
            
            self._status_history.append(RobotStatus(
                state=self._status.state,
                position=Position(**self._status.position.to_dict()),
                battery_level=self._status.battery_level,
                speed=self._status.speed,
                temperature=self._status.temperature,
                error_code=self._status.error_code,
                error_message=self._status.error_message,
                timestamp=self._status.timestamp
            ))
            
            if len(self._status_history) > self._max_history:
                self._status_history.pop(0)
            
            if self._status.battery_level < 20:
                self._event_bus.publish(Event(EventType.BATTERY_LOW, 
                                             {"level": self._status.battery_level}))
    
    def get_status_json(self) -> str:
        with self._lock:
            return json.dumps(self._status.to_dict(), indent=2)
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        with self._lock:
            return [s.to_dict() for s in self._status_history[-limit:]]
