"""
任务调度系统
支持多任务调度、优先级管理、任务状态跟踪
"""

import threading
import time
import uuid
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import PriorityQueue, Empty
import logging
import json

logger = logging.getLogger("TaskScheduler")


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    IDLE = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    task_id: str
    task_type: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    params: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    def __lt__(self, other):
        if self.priority == other.priority:
            return self.created_at < other.created_at
        return self.priority.value < other.priority.value


class TaskExecutor:
    def __init__(self, task: Task, robot_controller):
        self.task = task
        self.robot_controller = robot_controller
        self._cancelled = False
    
    def execute(self) -> Any:
        self.task.status = TaskStatus.RUNNING
        self.task.started_at = datetime.now()
        
        try:
            if self.task.task_type == "patrol":
                result = self._execute_patrol()
            elif self.task.task_type == "scan":
                result = self._execute_scan()
            elif self.task.task_type == "identify":
                result = self._execute_identify()
            elif self.task.task_type == "eradicate":
                result = self._execute_eradicate()
            elif self.task.task_type == "navigate":
                result = self._execute_navigate()
            elif self.task.task_type == "charge":
                result = self._execute_charge()
            else:
                result = {"success": False, "error": f"Unknown task type: {self.task.task_type}"}
            
            if not self._cancelled:
                self.task.status = TaskStatus.COMPLETED
                self.task.progress = 100.0
                self.task.result = result
                self.task.completed_at = datetime.now()
                return result
            
        except Exception as e:
            self.task.status = TaskStatus.FAILED
            self.task.error = str(e)
            logger.error(f"Task {self.task.task_id} failed: {e}")
            
            if self.task.retry_count < self.task.max_retries:
                self.task.retry_count += 1
                self.task.status = TaskStatus.PENDING
                logger.info(f"Task {self.task.task_id} will retry ({self.task.retry_count}/{self.task.max_retries})")
            
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Task cancelled"}
    
    def _execute_patrol(self) -> Dict[str, Any]:
        waypoints = self.task.params.get("waypoints", [])
        if not waypoints:
            return {"success": False, "error": "No waypoints provided"}
        
        for i, wp in enumerate(waypoints):
            if self._cancelled:
                break
            
            self.task.progress = (i / len(waypoints)) * 100
            self.robot_controller.navigate_to(wp["x"], wp["y"])
            
            while not self._check_navigation_complete() and not self._cancelled:
                time.sleep(0.5)
        
        return {"success": True, "waypoints_visited": len(waypoints)}
    
    def _execute_scan(self) -> Dict[str, Any]:
        duration = self.task.params.get("duration", 30)
        start_time = time.time()
        
        while time.time() - start_time < duration and not self._cancelled:
            self.task.progress = ((time.time() - start_time) / duration) * 100
            time.sleep(0.5)
        
        detections = self.robot_controller.scan_for_targets()
        return {"success": True, "detections": detections, "scan_duration": duration}
    
    def _execute_identify(self) -> Dict[str, Any]:
        targets = self.task.params.get("targets", [])
        results = []
        
        for i, target in enumerate(targets):
            if self._cancelled:
                break
            
            self.task.progress = (i / len(targets)) * 100
            result = self.robot_controller.identify_target(target)
            results.append(result)
        
        return {"success": True, "identifications": results}
    
    def _execute_eradicate(self) -> Dict[str, Any]:
        targets = self.task.params.get("targets", [])
        eradicated = 0
        
        for i, target in enumerate(targets):
            if self._cancelled:
                break
            
            self.task.progress = (i / len(targets)) * 100
            
            self.robot_controller.navigate_to(target["x"], target["y"])
            while not self._check_navigation_complete() and not self._cancelled:
                time.sleep(0.3)
            
            if not self._cancelled:
                success = self.robot_controller.fire_laser(duration=0.5)
                if success:
                    eradicated += 1
                time.sleep(1.0)
        
        return {"success": True, "eradicated_count": eradicated, "total_targets": len(targets)}
    
    def _execute_navigate(self) -> Dict[str, Any]:
        x = self.task.params.get("x", 0)
        y = self.task.params.get("y", 0)
        
        self.robot_controller.navigate_to(x, y)
        
        while not self._check_navigation_complete() and not self._cancelled:
            time.sleep(0.3)
        
        return {"success": True, "position": {"x": x, "y": y}}
    
    def _execute_charge(self) -> Dict[str, Any]:
        target_battery = self.task.params.get("target_battery", 100)
        
        while self.robot_controller.get_battery_level() < target_battery and not self._cancelled:
            battery = self.robot_controller.get_battery_level()
            self.task.progress = battery
            time.sleep(5.0)
        
        return {"success": True, "battery_level": self.robot_controller.get_battery_level()}
    
    def _check_navigation_complete(self) -> bool:
        status = self.robot_controller.get_robot_status()
        return status.get("state") == "ready"
    
    def cancel(self):
        self._cancelled = True


class TaskScheduler:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self._task_queue: PriorityQueue = PriorityQueue()
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        self._executor_thread: Optional[threading.Thread] = None
        
        self._tasks: Dict[str, Task] = {}
        self._active_task: Optional[Task] = None
        self._task_history: List[Task] = []
        self._lock = threading.Lock()
        
        self._current_executor: Optional[TaskExecutor] = None
        self._robot_controller = None
    
    def set_robot_controller(self, controller):
        self._robot_controller = controller
    
    def start(self):
        if not self._running:
            self._running = True
            self._scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True)
            self._scheduler_thread.start()
            self._executor_thread = threading.Thread(target=self._execute_loop, daemon=True)
            self._executor_thread.start()
            logger.info("Task scheduler started")
    
    def stop(self):
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=2.0)
        if self._executor_thread:
            self._executor_thread.join(timeout=2.0)
        logger.info("Task scheduler stopped")
    
    def submit_task(self, task_type: str, priority: TaskPriority = TaskPriority.NORMAL,
                   params: Optional[Dict[str, Any]] = None, task_id: Optional[str] = None) -> str:
        task_id = task_id or str(uuid.uuid4())[:8]
        task = Task(
            task_id=task_id,
            task_type=task_type,
            priority=priority,
            params=params or {}
        )
        
        with self._lock:
            self._tasks[task_id] = task
            self._task_queue.put(task)
        
        logger.info(f"Task submitted: {task_id} ({task_type})")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    task.status = TaskStatus.CANCELLED
                    if self._current_executor:
                        self._current_executor.cancel()
                    return True
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                return {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "priority": task.priority.name,
                    "status": task.status.value,
                    "progress": task.progress,
                    "result": task.result,
                    "error": task.error
                }
        return None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "task_type": t.task_type,
                    "priority": t.priority.name,
                    "status": t.status.value,
                    "progress": t.progress
                }
                for t in self._tasks.values()
            ]
    
    def _schedule_loop(self):
        while self._running:
            try:
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Schedule loop error: {e}")
    
    def _execute_loop(self):
        while self._running:
            try:
                if self._active_task and self._active_task.status == TaskStatus.RUNNING:
                    time.sleep(0.1)
                    continue
                
                try:
                    task = self._task_queue.get(timeout=0.5)
                except Empty:
                    continue
                
                with self._lock:
                    if task.status == TaskStatus.CANCELLED:
                        continue
                    self._active_task = task
                    self._current_executor = TaskExecutor(task, self._robot_controller)
                
                result = self._current_executor.execute()
                
                with self._lock:
                    self._task_history.append(task)
                    if len(self._task_history) > 1000:
                        self._task_history.pop(0)
                    self._active_task = None
                    self._current_executor = None
                
                self.event_bus.publish(Event(
                    EventType.TASK_COMPLETE,
                    {"task_id": task.task_id, "result": result}
                ))
                
            except Exception as e:
                logger.error(f"Execute loop error: {e}")
                time.sleep(0.5)


class MissionPlanner:
    def __init__(self, task_scheduler: TaskScheduler, event_bus):
        self.task_scheduler = task_scheduler
        self.event_bus = event_bus
        self._mission_queue: List[Dict] = []
        self._lock = threading.Lock()
    
    def create_patrol_mission(self, waypoints: List[Dict[str, float]], 
                             priority: TaskPriority = TaskPriority.NORMAL) -> str:
        task_id = self.task_scheduler.submit_task(
            task_type="patrol",
            priority=priority,
            params={"waypoints": waypoints}
        )
        return task_id
    
    def create_scan_mission(self, duration: int = 30,
                           priority: TaskPriority = TaskPriority.NORMAL) -> str:
        task_id = self.task_scheduler.submit_task(
            task_type="scan",
            priority=priority,
            params={"duration": duration}
        )
        return task_id
    
    def create_eradication_mission(self, targets: List[Dict[str, Any]],
                                   priority: TaskPriority = TaskPriority.HIGH) -> str:
        task_id = self.task_scheduler.submit_task(
            task_type="eradicate",
            priority=priority,
            params={"targets": targets}
        )
        return task_id
    
    def create_navigation_mission(self, x: float, y: float,
                                 priority: TaskPriority = TaskPriority.NORMAL) -> str:
        task_id = self.task_scheduler.submit_task(
            task_type="navigate",
            priority=priority,
            params={"x": x, "y": y}
        )
        return task_id
    
    def create_full_operation_mission(self, waypoints: List[Dict[str, float]],
                                      scan_interval: int = 30,
                                      priority: TaskPriority = TaskPriority.HIGH) -> List[str]:
        task_ids = []
        
        patrol_id = self.create_patrol_mission(waypoints, priority)
        task_ids.append(patrol_id)
        
        scan_id = self.create_scan_mission(scan_interval, TaskPriority.NORMAL)
        task_ids.append(scan_id)
        
        return task_ids
