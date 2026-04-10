#!/usr/bin/env python3
"""
RayMind OS - 整合界面
集成状态监控+控制+日志
"""
import sys
import os
import math
import random
import time
import threading

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton,
                             QGroupBox, QListWidget, QTextEdit, QProgressBar,
                             QTabWidget, QLineEdit, QInputDialog, QGraphicsView, QGraphicsScene)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont, QPen, QBrush, QPainter

def main():
    try:
        from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                     QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                                     QGroupBox, QListWidget, QTextEdit, QProgressBar,
                                     QTabWidget, QLineEdit, QInputDialog)
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QPalette, QColor, QFont
    except ImportError:
        print("需要安装PyQt5: pip3 install PyQt5")
        print("或者运行Web版: python3 raymind/web_gui.py")
        sys.exit(1)

    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from ai import AIManager
        AI_AVAILABLE = True
    except ImportError:
        AI_AVAILABLE = False
        print("AI模块不可用，将使用模拟模式")


    class RobotCore:
        
        def __init__(self):
            self.state = "idle"
            self.position = {"x": 0.0, "y": 0.0, "yaw": 0.0}
            self.left_track = 0.0
            self.right_track = 0.0
            self.battery = 100.0
            self.targets = []
            self.running = False
        
        def start(self):
            self.running = True
            self.state = "ready"
            return True
        
        def stop(self):
            self.running = False
            self.left_track = 0
            self.right_track = 0
            self.state = "idle"
            return True
        
        def scan(self, duration=2):
            if self.state != "ready":
                return []
            self.state = "scanning"
            time.sleep(duration)
            self.targets = []
            for i in range(random.randint(3, 8)):
                self.targets.append({
                    "id": i+1,
                    "x": random.uniform(-4, 4),
                    "y": random.uniform(-4, 4),
                    "type": "weed",
                    "confidence": random.uniform(0.6, 0.99)
                })
            self.state = "ready"
            return self.targets
        
        def eradicate(self, targets=None):
            if targets is None:
                targets = self.targets
            if not targets:
                return 0
            self.state = "executing"
            count = 0
            for t in targets:
                time.sleep(0.3)
                count += 1
            self.state = "ready"
            return count


    class RayMindGUI(QMainWindow):
        def __init__(self):
            super().__init__()
            self.robot = RobotCore()
            self.simulator = None
            self.sim_running = False
            self.ros_manager = None
            self.initUI()
            self.startUpdateTimer()
            
        def initUI(self):
            self.setWindowTitle("RayMind 智能农田机器人")
            self.setGeometry(100, 50, 1000, 700)
            self.setStyleSheet("""
                QMainWindow { background-color: #0d1117; }
                QLabel { color: #c9d1d9; }
                QTabWidget::pane { border: 1px solid #30363d; background: #161b22; }
                QTabBar::tab { 
                    background: #21262d; color: #8b949e; padding: 10px 20px; 
                    border: 1px solid #30363d; margin-right: 2px;
                }
                QTabBar::tab:selected { background: #1f6feb; color: white; }
                QPushButton {
                    background-color: #238636; color: white; border: none;
                    padding: 10px 15px; border-radius: 6px; font-weight: bold;
                }
                QPushButton:hover { background-color: #2ea043; }
                QPushButton#btnRed { background-color: #da3633; }
                QPushButton#btnRed:hover { background-color: #f85149; }
                QPushButton#btnYellow { background-color: #d29922; color: #0d1117; }
                QGroupBox { 
                    color: #58a6ff; border: 1px solid #30363d; border-radius: 8px;
                    margin-top: 10px; font-weight: bold;
                }
                QTextEdit, QListWidget { background-color: #0d1117; color: #7ee787; border: 1px solid #30363d; }
                QProgressBar { border: none; background: #21262d; }
                QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #238636,stop:1 #58a6ff); }
            """)
            
            central = QWidget()
            self.setCentralWidget(central)
            layout = QHBoxLayout(central)
            
            tabs = QTabWidget()
            tabs.addTab(self.createStatusTab(), "📊 状态")
            tabs.addTab(self.createControlTab(), "� 控制")
            tabs.addTab(self.createLogTab(), "📝 日志")
            
            layout.addWidget(tabs)
            self.log("RayMind系统已启动")
        
        def createStatusTab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            header = QLabel("🌾 RayMind 智能农田机器人")
            header.setStyleSheet("font-size: 22px; font-weight: bold; color: #58a6ff; padding: 15px;")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            conn_btn_layout = QHBoxLayout()
            self.btn_ros_connect = QPushButton("🔗 连接ROS2")
            self.btn_ros_connect.setFixedHeight(45)
            self.btn_ros_connect.setStyleSheet("background: #238636; color: white; font-size: 16px; font-weight: bold; border-radius: 8px;")
            self.btn_ros_connect.clicked.connect(self.connectROS2)
            conn_btn_layout.addWidget(self.btn_ros_connect)
            
            self.btn_ros_disconnect = QPushButton("🔌 断开")
            self.btn_ros_disconnect.setFixedHeight(45)
            self.btn_ros_disconnect.setEnabled(False)
            self.btn_ros_disconnect.setStyleSheet("background: #da3633; color: white; font-size: 16px; font-weight: bold; border-radius: 8px;")
            self.btn_ros_disconnect.clicked.connect(self.disconnectROS2)
            conn_btn_layout.addWidget(self.btn_ros_disconnect)
            layout.addLayout(conn_btn_layout)
            
            status_grid = QGridLayout()
            
            self.state_label = QLabel("未连接")
            self.state_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #f85149;")
            status_grid.addWidget(QLabel("状态:"), 0, 0)
            status_grid.addWidget(self.state_label, 0, 1)
            
            self.battery_label = QLabel("--")
            self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #8b949e;")
            status_grid.addWidget(QLabel("🔋 电池:"), 1, 0)
            status_grid.addWidget(self.battery_label, 1, 1)
            
            self.x_label = QLabel("X: --")
            self.y_label = QLabel("Y: --")
            self.yaw_label = QLabel("航向: --")
            for label in [self.x_label, self.y_label, self.yaw_label]:
                label.setStyleSheet("font-size: 16px; color: #8b949e;")
            status_grid.addWidget(self.x_label, 2, 0)
            status_grid.addWidget(self.y_label, 2, 1)
            status_grid.addWidget(self.yaw_label, 3, 0, 1, 2)
            
            layout.addLayout(status_grid)
            
            sensor_grid = QGridLayout()
            sensor_grid.setSpacing(10)
            
            self.sensor_labels = {}
            sensors = [
                ("LiDAR", "🔴"),
                ("相机", "🔴"), 
                ("IMU", "🔴"),
                ("GPS", "🔴")
            ]
            
            for i, (name, icon) in enumerate(sensors):
                btn = QPushButton(f"{icon} {name}")
                btn.setFixedHeight(40)
                btn.setStyleSheet("background: #21262d; color: #f85149; border: 1px solid #30363d; border-radius: 5px;")
                btn.setEnabled(False)
                self.sensor_labels[name] = btn
                sensor_grid.addWidget(btn, i // 2, i % 2)
            
            layout.addLayout(sensor_grid)
            
            return w
        
        def createControlTab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            title = QLabel("🎮 机器人控制")
            title.setStyleSheet("font-size: 20px; font-weight: bold; color: #58a6ff; padding: 10px;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            control_grid = QGridLayout()
            control_grid.setSpacing(15)
            
            btn_forward = QPushButton("▲")
            btn_forward.setFixedSize(80, 60)
            btn_forward.setStyleSheet("background: #238636; color: white; font-size: 24px; border-radius: 10px;")
            btn_forward.pressed.connect(self.onTrackForward)
            btn_forward.released.connect(self.onTrackStop)
            control_grid.addWidget(btn_forward, 0, 1)
            
            btn_left = QPushButton("◀")
            btn_left.setFixedSize(80, 60)
            btn_left.setStyleSheet("background: #1f6feb; color: white; font-size: 24px; border-radius: 10px;")
            btn_left.pressed.connect(self.onTrackLeft)
            btn_left.released.connect(self.onTrackStop)
            control_grid.addWidget(btn_left, 1, 0)
            
            btn_stop = QPushButton("⏹")
            btn_stop.setFixedSize(80, 60)
            btn_stop.setStyleSheet("background: #da3633; color: white; font-size: 24px; border-radius: 10px;")
            btn_stop.clicked.connect(self.onTrackStop)
            control_grid.addWidget(btn_stop, 1, 1)
            
            btn_right = QPushButton("▶")
            btn_right.setFixedSize(80, 60)
            btn_right.setStyleSheet("background: #1f6feb; color: white; font-size: 24px; border-radius: 10px;")
            btn_right.pressed.connect(self.onTrackRight)
            btn_right.released.connect(self.onTrackStop)
            control_grid.addWidget(btn_right, 1, 2)
            
            btn_backward = QPushButton("▼")
            btn_backward.setFixedSize(80, 60)
            btn_backward.setStyleSheet("background: #6e7681; color: white; font-size: 24px; border-radius: 10px;")
            btn_backward.pressed.connect(self.onTrackBackward)
            btn_backward.released.connect(self.onTrackStop)
            control_grid.addWidget(btn_backward, 2, 1)
            
            layout.addLayout(control_grid)
            
            track_layout = QHBoxLayout()
            
            left_layout = QVBoxLayout()
            left_layout.addWidget(QLabel("左履带"))
            self.left_slider = QProgressBar()
            self.left_slider.setRange(-100, 100)
            self.left_slider.setValue(0)
            self.left_slider.setFixedHeight(25)
            self.left_slider.setStyleSheet("QProgressBar { border-radius: 5px; } QProgressBar::chunk { background: #58a6ff; }")
            left_layout.addWidget(self.left_slider)
            self.left_label = QLabel("0%")
            self.left_label.setAlignment(Qt.AlignCenter)
            self.left_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            left_layout.addWidget(self.left_label)
            
            right_layout = QVBoxLayout()
            right_layout.addWidget(QLabel("右履带"))
            self.right_slider = QProgressBar()
            self.right_slider.setRange(-100, 100)
            self.right_slider.setValue(0)
            self.right_slider.setFixedHeight(25)
            self.right_slider.setStyleSheet("QProgressBar { border-radius: 5px; } QProgressBar::chunk { background: #58a6ff; }")
            right_layout.addWidget(self.right_slider)
            self.right_label = QLabel("0%")
            self.right_label.setAlignment(Qt.AlignCenter)
            self.right_label.setStyleSheet("font-size: 18px; font-weight: bold;")
            right_layout.addWidget(self.right_label)
            
            track_layout.addLayout(left_layout)
            track_layout.addLayout(right_layout)
            layout.addLayout(track_layout)
            
            return w
            
            return w
        
        def onTrackForward(self):
            self.robot.left_track = 80
            self.robot.right_track = 80
            self.left_slider.setValue(80)
            self.right_slider.setValue(80)
            self.left_label.setText("80%")
            self.right_label.setText("80%")
            self.log("履带: 前进")
        
        def onTrackBackward(self):
            self.robot.left_track = -60
            self.robot.right_track = -60
            self.left_slider.setValue(-60)
            self.right_slider.setValue(-60)
            self.left_label.setText("-60%")
            self.right_label.setText("-60%")
            self.log("履带: 后退")
        
        def onTrackLeft(self):
            self.robot.left_track = -50
            self.robot.right_track = 50
            self.left_slider.setValue(-50)
            self.right_slider.setValue(50)
            self.left_label.setText("-50%")
            self.right_label.setText("50%")
            self.log("履带: 左转")
        
        def onTrackRight(self):
            self.robot.left_track = 50
            self.robot.right_track = -50
            self.left_slider.setValue(50)
            self.right_slider.setValue(-50)
            self.left_label.setText("50%")
            self.right_label.setText("-50%")
            self.log("履带: 右转")
        
        def onTrackStop(self):
            self.robot.left_track = 0
            self.robot.right_track = 0
            self.left_slider.setValue(0)
            self.right_slider.setValue(0)
            self.left_label.setText("0%")
            self.right_label.setText("0%")
            self.log("履带: 停止")
            if hasattr(self, 'simulator') and self.simulator:
                self.simulator.set_track(0, 0)
        
        def createROS2ControlGroup(self):
            group = QGroupBox("🤖 ROS2 控制")
            layout = QVBoxLayout(group)
            
            btn_layout = QHBoxLayout()
            
            self.btn_ros_connect = QPushButton("🔗 连接")
            self.btn_ros_connect.clicked.connect(self.connectROS2)
            btn_layout.addWidget(self.btn_ros_connect)
            
            self.btn_ros_disconnect = QPushButton("🔌 断开")
            self.btn_ros_disconnect.clicked.connect(self.disconnectROS2)
            self.btn_ros_disconnect.setEnabled(False)
            btn_layout.addWidget(self.btn_ros_disconnect)
            
            layout.addLayout(btn_layout)
            
            self.ros_status = QLabel("状态: 未连接")
            layout.addWidget(self.ros_status)
            
            return group
        
        def connectROS2(self):
            try:
                from ros2_interface import ROS2Manager
                self.ros_manager = ROS2Manager('raymind_gui')
                if self.ros_manager.start():
                    self.state_label.setText("🟢 在线")
                    self.state_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #7ee787;")
                    self.btn_ros_connect.setEnabled(False)
                    self.btn_ros_disconnect.setEnabled(True)
                    self.log("ROS2已连接")
                else:
                    self.log("ROS2连接失败")
            except Exception as e:
                self.log(f"ROS2错误: {e}")
        
        def disconnectROS2(self):
            if hasattr(self, 'ros_manager'):
                self.ros_manager.stop()
                self.state_label.setText("🔴 未连接")
                self.state_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #f85149;")
                self.btn_ros_connect.setEnabled(True)
                self.btn_ros_disconnect.setEnabled(False)
                self.log("ROS2已断开")
        
        def createLogTab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            layout.addWidget(self.log_area)
            
            return w
        
        def startUpdateTimer(self):
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateStatus)
            self.timer.start(100)
        
        def updateStatus(self):
            if hasattr(self, 'ros_manager') and self.ros_manager.is_running():
                data = self.ros_manager.get_sensor_data()
                
                self.state_label.setText("🟢 在线")
                self.state_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #7ee787;")
                
                if 'battery' in data:
                    battery = data.get('battery', 0)
                    self.battery_label.setText("{:.0f}%".format(battery))
                    
                    if battery < 20:
                        self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f85149;")
                    elif battery < 50:
                        self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f0883e;")
                    else:
                        self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #7ee787;")
                
                if 'odom' in data:
                    pos = data['odom']['position']
                    self.x_label.setText("X: {:.2f}m".format(pos['x']))
                    self.y_label.setText("Y: {:.2f}m".format(pos['y']))
                    ori = data['odom']['orientation']
                    yaw = math.atan2(2*(ori['w']*ori['z']), 1-2*ori['z']*ori['z'])
                    self.yaw_label.setText("航向: {:.0f}°".format(math.degrees(yaw)))
                    
                    for label in [self.x_label, self.y_label, self.yaw_label]:
                        label.setStyleSheet("font-size: 16px; color: #c9d1d9;")
                
                if 'laser' in data:
                    self.sensor_labels['LiDAR'].setText("🟢 LiDAR")
                    self.sensor_labels['LiDAR'].setStyleSheet("background: #238636; color: white; border-radius: 5px;")
                
                if hasattr(self, 'sensor_labels'):
                    for name, btn in self.sensor_labels.items():
                        if btn.text().startswith("🔴"):
                            if name == 'LiDAR' and 'laser' not in data:
                                btn.setText("🔴 LiDAR")
                                btn.setStyleSheet("background: #21262d; color: #f85149; border: 1px solid #30363d; border-radius: 5px;")
            else:
                self.state_label.setText("🔴 未连接")
                self.state_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #f85149;")
                self.battery_label.setText("--")
                self.battery_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #8b949e;")
            
            self.left_slider.setValue(int(self.robot.left_track))
            self.right_slider.setValue(int(self.robot.right_track))
            self.left_label.setText("{}%".format(int(self.robot.left_track)))
            self.right_label.setText("{}%".format(int(self.robot.right_track)))
            
            if hasattr(self, 'ros_manager') and self.ros_manager.is_running():
                data = self.ros_manager.get_sensor_data()
                if 'odom' in data:
                    pos = data['odom']['position']
                    self.x_label.setText("X: {:.2f}m".format(pos['x']))
                    self.y_label.setText("Y: {:.2f}m".format(pos['y']))
                    ori = data['odom']['orientation']
                    import math
                    yaw = math.atan2(2*(ori['w']*ori['z']), 1-2*ori['z']*ori['z'])
                    self.yaw_label.setText("航向: {:.0f}°".format(math.degrees(yaw)))
                    self.ros_status_label.setText("🟢 实时")
                if 'laser' in data:
                    self._update_sensor("LiDAR", True, f"{len(data['laser']['ranges'])}点")
                else:
                    self._update_sensor("LiDAR", False)
                if 'gps' in data:
                    gps = data['gps']
                    self._update_sensor("GPS", True, f"{gps['latitude']:.4f}")
                else:
                    self._update_sensor("GPS", False)
                self._update_sensor("IMU", True if 'imu' in data else False)
                self._update_sensor("相机", True if 'camera' in data else False)
            else:
                self.ros_status_label.setText("🔴 未连接")
        
        def _update_sensor(self, name: str, connected: bool, info: str = ""):
            if hasattr(self, 'sensor_labels') and name in self.sensor_labels:
                if connected:
                    self.sensor_labels[name].setText(info if info else "已连接")
                    self.sensor_labels[name].setStyleSheet("color: #7ee787;")
                else:
                    self.sensor_labels[name].setText("未连接")
                    self.sensor_labels[name].setStyleSheet("color: #f85149;")
        
        def onStart(self):
            self.robot.start()
            self.log("系统启动")
        
        def onStop(self):
            self.robot.stop()
            self.log("系统停止")
        
        def onScan(self):
            self.log("开始扫描...")
            targets = self.robot.scan(duration=2)
            self.target_list.clear()
            for t in targets:
                self.target_list.addItem("目标{}: {} {:.0%}".format(t["id"], t["type"], t["confidence"]))
            self.log("发现 {} 个目标".format(len(targets)))
        
        def onEradicate(self):
            if not self.robot.targets:
                self.log("无目标可清除")
                return
            self.log("开始清除 {} 个目标...".format(len(self.robot.targets)))
            count = self.robot.eradicate()
            self.target_list.clear()
            self.robot.targets = []
            self.log("清除完成: {} 个".format(count))
        
        def log(self, msg):
            ts = time.strftime("%H:%M:%S")
            self.log_area.append("[{}] {}".format(ts, msg))
            self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        
        def createWeedDetectTab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            header = QLabel("🌿 杂草识别系统")
            header.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            self.weed_status = QLabel("📷 等待图像输入...")
            layout.addWidget(self.weed_status)
            
            result_group = QGroupBox("📊 识别结果")
            result_layout = QVBoxLayout(result_group)
            
            self.weed_list = QListWidget()
            result_layout.addWidget(self.weed_list)
            
            stats_layout = QHBoxLayout()
            self.total_weeds = QLabel("杂草总数: 0")
            self.weed_confidence = QLabel("平均置信度: 0%")
            stats_layout.addWidget(self.total_weeds)
            stats_layout.addWidget(self.weed_confidence)
            result_layout.addLayout(stats_layout)
            
            layout.addWidget(result_group)
            
            btn_layout = QHBoxLayout()
            
            btn_start = QPushButton("🔍 开始识别")
            btn_start.clicked.connect(self.startWeedDetection)
            btn_layout.addWidget(btn_start)
            
            btn_clear = QPushButton("🗑 清除结果")
            btn_clear.clicked.connect(self.clearWeedResults)
            btn_layout.addWidget(btn_clear)
            
            layout.addLayout(btn_layout)
            
            layout.addStretch()
            
            return w
        
        def startWeedDetection(self):
            self.weed_status.setText("🔍 正在识别...")
            self.weed_list.clear()
            
            import random
            weed_types = ["牛筋草", "马唐", "稗草", "狗尾草", "香附子", "空心莲子草"]
            
            count = random.randint(3, 8)
            total_conf = 0
            
            for i in range(count):
                weed_type = random.choice(weed_types)
                confidence = random.randint(75, 98)
                x, y = random.randint(100, 700), random.randint(100, 500)
                total_conf += confidence
                
                self.weed_list.addItem(
                    f"目标{i+1}: {weed_type} | 置信度: {confidence}% | 位置: ({x}, {y})"
                )
            
            avg_conf = total_conf // count if count > 0 else 0
            self.total_weeds.setText(f"杂草总数: {count}")
            self.weed_confidence.setText(f"平均置信度: {avg_conf}%")
            self.weed_status.setText(f"✅ 识别完成，发现 {count} 个杂草目标")
            self.log(f"杂草识别: 发现 {count} 个目标")
        
        def clearWeedResults(self):
            self.weed_list.clear()
            self.total_weeds.setText("杂草总数: 0")
            self.weed_confidence.setText("平均置信度: 0%")
            self.weed_status.setText("📷 等待图像输入...")
        
        def createROS2Tab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            header = QLabel("🤖 ROS2 控制")
            header.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            self.ros_status = QLabel("🔴 ROS2 未连接")
            layout.addWidget(self.ros_status)
            
            btn_layout = QHBoxLayout()
            
            self.btn_ros_connect = QPushButton("🔗 连接ROS2")
            self.btn_ros_connect.clicked.connect(self.toggleROS2)
            btn_layout.addWidget(self.btn_ros_connect)
            
            self.btn_ros_disconnect = QPushButton("🔌 断开")
            self.btn_ros_disconnect.clicked.connect(self.disconnectROS2)
            self.btn_ros_disconnect.setEnabled(False)
            btn_layout.addWidget(self.btn_ros_disconnect)
            
            layout.addLayout(btn_layout)
            
            sensor_group = QGroupBox("📡 传感器数据")
            sensor_layout = QVBoxLayout(sensor_group)
            
            self.laser_label = QLabel("激光雷达: 未连接")
            sensor_layout.addWidget(self.laser_label)
            
            self.odom_label = QLabel("里程计: 未连接")
            sensor_layout.addWidget(self.odom_label)
            
            self.gps_label = QLabel("GPS: 未连接")
            sensor_layout.addWidget(self.gps_label)
            
            self.imu_label = QLabel("IMU: 未连接")
            sensor_layout.addWidget(self.imu_label)
            
            layout.addWidget(sensor_group)
            
            control_group = QGroupBox("🎮 远程控制")
            control_layout = QGridLayout(control_group)
            
            btn_forward = QPushButton("⬆️ 前进")
            btn_forward.pressed.connect(lambda: self.rosMove(0.3, 0))
            btn_forward.released.connect(lambda: self.rosMove(0, 0))
            control_layout.addWidget(btn_forward, 0, 1)
            
            btn_left = QPushButton("⬅️ 左转")
            btn_left.pressed.connect(lambda: self.rosMove(0, 0.5))
            btn_left.released.connect(lambda: self.rosMove(0, 0))
            control_layout.addWidget(btn_left, 1, 0)
            
            btn_stop = QPushButton("⏹ 停止")
            btn_stop.clicked.connect(lambda: self.rosMove(0, 0))
            control_layout.addWidget(btn_stop, 1, 1)
            
            btn_right = QPushButton("➡️ 右转")
            btn_right.pressed.connect(lambda: self.rosMove(0, -0.5))
            btn_right.released.connect(lambda: self.rosMove(0, 0))
            control_layout.addWidget(btn_right, 1, 2)
            
            btn_backward = QPushButton("⬇️ 后退")
            btn_backward.pressed.connect(lambda: self.rosMove(-0.3, 0))
            btn_backward.released.connect(lambda: self.rosMove(0, 0))
            control_layout.addWidget(btn_backward, 2, 1)
            
            layout.addWidget(control_group)
            
            layout.addStretch()
            
            return w
        
        def toggleROS2(self):
            try:
                from ros2_interface import ROS2Manager
                self.ros_manager = ROS2Manager('raymind_gui')
                if self.ros_manager.start():
                    self.ros_status.setText("🟢 ROS2 已连接")
                    self.btn_ros_connect.setEnabled(False)
                    self.btn_ros_disconnect.setEnabled(True)
                    self.log("ROS2 connected")
                    self.updateROS2Sensors()
                else:
                    self.ros_status.setText("🔴 ROS2 连接失败")
            except Exception as e:
                self.ros_status.setText(f"🔴 ROS2 不可用: {str(e)[:30]}")
                self.log(f"ROS2 error: {e}")
        
        def disconnectROS2(self):
            if hasattr(self, 'ros_manager'):
                self.ros_manager.stop()
                self.ros_status.setText("🔴 ROS2 未连接")
                self.btn_ros_connect.setEnabled(True)
                self.btn_ros_disconnect.setEnabled(False)
                self.log("ROS2 disconnected")
        
        def rosMove(self, linear: float, angular: float):
            if hasattr(self, 'ros_manager') and self.ros_manager.is_running():
                self.ros_manager.move_robot(linear=linear, angular=angular)
        
        def updateROS2Sensors(self):
            if hasattr(self, 'ros_manager') and self.ros_manager.is_running():
                data = self.ros_manager.get_sensor_data()
                
                if 'laser' in data:
                    self.laser_label.setText(f"激光雷达: {len(data['laser']['ranges'])} 点")
                if 'odom' in data:
                    pos = data['odom']['position']
                    self.odom_label.setText(f"里程计: ({pos['x']:.2f}, {pos['y']:.2f})")
                if 'gps' in data:
                    gps = data['gps']
                    self.gps_label.setText(f"GPS: {gps['latitude']:.6f}, {gps['longitude']:.6f}")
                if 'imu' in data:
                    self.imu_label.setText("IMU: 已连接")
        
        def createNetworkTab(self):
            w = QWidget()
            layout = QVBoxLayout(w)
            
            header = QLabel("📶 网络控制")
            header.setStyleSheet("font-size: 18px; font-weight: bold; color: #58a6ff;")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            self.net_status = QLabel("🔴 未连接")
            layout.addWidget(self.net_status)
            
            wifi_group = QGroupBox("📡 WiFi")
            wifi_layout = QVBoxLayout(wifi_group)
            
            self.wifi_ssid = QLabel("SSID: 未连接")
            wifi_layout.addWidget(self.wifi_ssid)
            
            self.wifi_signal = QLabel("信号: -")
            wifi_layout.addWidget(self.wifi_signal)
            
            self.wifi_ip = QLabel("IP: -")
            wifi_layout.addWidget(self.wifi_ip)
            
            wifi_btn_layout = QHBoxLayout()
            btn_wifi_scan = QPushButton("🔍 扫描")
            btn_wifi_scan.clicked.connect(self.scanWiFi)
            wifi_btn_layout.addWidget(btn_wifi_scan)
            
            btn_wifi_refresh = QPushButton("🔄 刷新")
            btn_wifi_refresh.clicked.connect(self.refreshNetwork)
            wifi_btn_layout.addWidget(btn_wifi_refresh)
            
            wifi_layout.addLayout(wifi_btn_layout)
            layout.addWidget(wifi_group)
            
            cellular_group = QGroupBox("📱 5G/4G")
            cellular_layout = QVBoxLayout(cellular_group)
            
            self.cellular_type = QLabel("网络类型: 未连接")
            cellular_layout.addWidget(self.cellular_type)
            
            self.cellular_signal = QLabel("信号强度: -")
            cellular_layout.addWidget(self.cellular_signal)
            
            self.cellular_ip = QLabel("IP: -")
            cellular_layout.addWidget(self.cellular_ip)
            
            layout.addWidget(cellular_group)
            
            relay_group = QGroupBox("🔗 远程透传")
            relay_layout = QVBoxLayout(relay_group)
            
            relay_btn_layout = QHBoxLayout()
            
            btn_start_server = QPushButton("🖥️ 启动服务器")
            btn_start_server.clicked.connect(self.startRelayServer)
            relay_btn_layout.addWidget(btn_start_server)
            
            btn_connect = QPushButton("📱 连接机器人")
            btn_connect.clicked.connect(self.connectToRelay)
            relay_btn_layout.addWidget(btn_connect)
            
            relay_layout.addLayout(relay_btn_layout)
            
            self.relay_status = QLabel("透传: 未启动")
            relay_layout.addWidget(self.relay_status)
            
            layout.addWidget(relay_group)
            
            layout.addStretch()
            
            return w
        
        def scanWiFi(self):
            try:
                from network import NetworkManager
                self.network_manager = NetworkManager()
                status = self.network_manager.get_status()
                
                if status.connected:
                    self.net_status.setText("🟢 已连接")
                    self.wifi_ssid.setText(f"SSID: {status.network_type.value}")
                    self.wifi_signal.setText(f"信号: {status.signal_strength}%")
                    self.wifi_ip.setText(f"IP: {status.ip_address}")
                    self.log("WiFi扫描完成")
                else:
                    self.net_status.setText("🔴 未连接")
            except Exception as e:
                self.log(f"WiFi扫描失败: {e}")
        
        def refreshNetwork(self):
            self.scanWiFi()
        
        def startRelayServer(self):
            try:
                from network import NetworkManager
                self.network_manager = NetworkManager()
                self.network_manager.start_relay_server(8888)
                self.relay_status.setText("🟢 服务器已启动: :8888")
                self.log("远程透传服务器已启动")
            except Exception as e:
                self.log(f"启动失败: {e}")
        
        def connectToRelay(self):
            ip, ok = QInputDialog.getText(self, "连接机器人", "请输入机器人IP地址:")
            if ok and ip:
                try:
                    from network import NetworkManager
                    self.network_manager = NetworkManager()
                    self.network_manager.connect_to_relay(ip, 8888)
                    self.relay_status.setText(f"🟢 已连接到: {ip}")
                    self.log(f"已连接到机器人: {ip}")
                except Exception as e:
                    self.log(f"连接失败: {e}")


    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    p = QPalette()
    p.setColor(QPalette.Window, QColor(13, 17, 23))
    p.setColor(QPalette.WindowText, QColor(201, 209, 217))
    app.setPalette(p)
    
    window = RayMindGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
