#!/usr/bin/env python3
"""
RayMind 仿真可视化界面
显示机器人、传感器数据、地图
"""

import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QPushButton,
                             QGroupBox, QTabWidget, QTextEdit, QSplitter)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene


class MapView(QGraphicsView):
    """地图视图"""
    
    def __init__(self, simulator=None):
        super().__init__()
        self.simulator = simulator
        self.scale_factor = 20.0
        self.setRenderHint(1)
        self.setDragMode(1)
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.setMinimumSize(600, 500)
        self.setStyleSheet("background-color: #1a1a2e;")
    
    def paintEvent(self, event):
        super().paintEvent(event)
        self.update()
    
    def drawMap(self, data):
        """绘制地图"""
        self.scene.clear()
        
        if not data:
            return
        
        env = data.get('environment', {})
        width = env.get('width', 50)
        height = env.get('height', 100)
        
        offset_x = self.width() / 2
        offset_y = self.height() / 2
        
        self.scene.addRect(
            -width/2 * self.scale_factor + offset_x,
            -height/2 * self.scale_factor + offset_y,
            width * self.scale_factor,
            height * self.scale_factor,
            QPen(QColor("#30363d")), 
            QBrush(QColor("#0d1117"))
        )
        
        obstacles = data.get('obstacles', [])
        for ox, oy, oradius, otype in obstacles:
            if otype == "weed":
                color = QColor("#f85149")
            elif otype == "rock":
                color = QColor("#8b949e")
            else:
                color = QColor("#58a6ff")
            
            self.scene.addEllipse(
                (ox - oradius) * self.scale_factor + offset_x,
                (oy - oradius) * self.scale_factor + offset_y,
                oradius * 2 * self.scale_factor,
                oradius * 2 * self.scale_factor,
                QPen(color),
                QBrush(color)
            )
        
        robot = data.get('robot', {})
        rx = robot.get('x', 0)
        ry = robot.get('y', 0)
        ryaw = robot.get('yaw', 0)
        
        px = rx * self.scale_factor + offset_x
        py = -ry * self.scale_factor + offset_y
        
        self.scene.addEllipse(px - 15, py - 15, 30, 30, 
                            QPen(QColor("#238636")), QBrush(QColor("#238636")))
        
        line_len = 40
        end_x = px + math.cos(ryaw) * line_len
        end_y = py - math.sin(ryaw) * line_len
        
        self.scene.addLine(px, py, end_x, end_y, 
                         QPen(QColor("#58a6ff"), 3))


class RayMindSimGUI(QMainWindow):
    """仿真GUI"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RayMind 仿真系统")
        self.setGeometry(100, 50, 1200, 800)
        
        self.init_simulator()
        self.initUI()
        self.start_simulation()
    
    def init_simulator(self):
        """初始化仿真器"""
        try:
            import sys
            sys.path.insert(0, '/home/meta/RayMind')
            from raymind.simulation import create_farm_simulation
            self.simulator = create_farm_simulation()
        except Exception as e:
            print(f"Simulation import failed: {e}")
            from raymind.simulation import RayMindSimulator, FarmEnvironment
            self.simulator = RayMindSimulator(FarmEnvironment())
    
    def initUI(self):
        """初始化UI"""
        self.setStyleSheet("""
            QMainWindow { background-color: #0d1117; }
            QLabel { color: #c9d1d9; }
            QGroupBox { 
                color: #58a6ff; 
                border: 1px solid #30363d;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #238636;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton:pressed { background-color: #238636; }
            QTextEdit {
                background-color: #161b22;
                color: #c9d1d9;
                border: 1px solid #30363d;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        header = QLabel("🎮 RayMind 仿真系统")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #58a6ff; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(header)
        
        control_group = QGroupBox("🎮 控制")
        control_layout = QVBoxLayout(control_group)
        
        btn_layout = QGridLayout()
        
        self.btn_forward = QPushButton("▲")
        self.btn_forward.setFixedSize(60, 50)
        self.btn_forward.pressed.connect(lambda: self.set_velocity(0.3, 0))
        self.btn_forward.released.connect(lambda: self.set_velocity(0, 0))
        btn_layout.addWidget(self.btn_forward, 0, 1)
        
        self.btn_left = QPushButton("◀")
        self.btn_left.setFixedSize(60, 50)
        self.btn_left.pressed.connect(lambda: self.set_velocity(0, 0.5))
        self.btn_left.released.connect(lambda: self.set_velocity(0, 0))
        btn_layout.addWidget(self.btn_left, 1, 0)
        
        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(60, 50)
        self.btn_stop.setStyleSheet("background-color: #da3633;")
        self.btn_stop.clicked.connect(lambda: self.set_velocity(0, 0))
        btn_layout.addWidget(self.btn_stop, 1, 1)
        
        self.btn_right = QPushButton("▶")
        self.btn_right.setFixedSize(60, 50)
        self.btn_right.pressed.connect(lambda: self.set_velocity(0, -0.5))
        self.btn_right.released.connect(lambda: self.set_velocity(0, 0))
        btn_layout.addWidget(self.btn_right, 1, 2)
        
        self.btn_backward = QPushButton("▼")
        self.btn_backward.setFixedSize(60, 50)
        self.btn_backward.pressed.connect(lambda: self.set_velocity(-0.3, 0))
        self.btn_backward.released.connect(lambda: self.set_velocity(0, 0))
        btn_layout.addWidget(self.btn_backward, 2, 1)
        
        control_layout.addLayout(btn_layout)
        
        track_layout = QHBoxLayout()
        
        left_layout_inner = QVBoxLayout()
        left_layout_inner.addWidget(QLabel("左履带"))
        self.left_bar = QLabel("0%")
        self.left_bar.setStyleSheet("color: #58a6ff; font-size: 16px; font-weight: bold;")
        left_layout_inner.addWidget(self.left_bar)
        
        right_layout_inner = QVBoxLayout()
        right_layout_inner.addWidget(QLabel("右履带"))
        self.right_bar = QLabel("0%")
        self.right_bar.setStyleSheet("color: #58a6ff; font-size: 16px; font-weight: bold;")
        right_layout_inner.addWidget(self.right_bar)
        
        track_layout.addLayout(left_layout_inner)
        track_layout.addLayout(right_layout_inner)
        control_layout.addLayout(track_layout)
        
        left_layout.addWidget(control_group)
        
        status_group = QGroupBox("📊 状态")
        status_layout = QGridLayout(status_group)
        
        status_layout.addWidget(QLabel("位置 X:"), 0, 0)
        self.x_label = QLabel("0.00m")
        status_layout.addWidget(self.x_label, 0, 1)
        
        status_layout.addWidget(QLabel("位置 Y:"), 1, 0)
        self.y_label = QLabel("0.00m")
        status_layout.addWidget(self.y_label, 1, 1)
        
        status_layout.addWidget(QLabel("航向:"), 2, 0)
        self.yaw_label = QLabel("0°")
        status_layout.addWidget(self.yaw_label, 2, 1)
        
        status_layout.addWidget(QLabel("速度:"), 3, 0)
        self.vel_label = QLabel("0.0 m/s")
        status_layout.addWidget(self.vel_label, 3, 1)
        
        status_layout.addWidget(QLabel("电池:"), 4, 0)
        self.battery_label = QLabel("100%")
        self.battery_label.setStyleSheet("color: #7ee787; font-weight: bold;")
        status_layout.addWidget(self.battery_label, 4, 1)
        
        status_layout.addWidget(QLabel("障碍物:"), 5, 0)
        self.obstacle_label = QLabel("0")
        status_layout.addWidget(self.obstacle_label, 5, 1)
        
        left_layout.addWidget(status_group)
        
        log_group = QGroupBox("📝 日志")
        log_layout = QVBoxLayout(log_group)
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(150)
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)
        left_layout.addWidget(log_group)
        
        left_layout.addStretch()
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        map_group = QGroupBox("🗺️ 地图视图")
        map_layout = QVBoxLayout(map_group)
        self.map_view = MapView(self.simulator)
        map_layout.addWidget(self.map_view)
        right_layout.addWidget(map_group)
        
        sensor_group = QGroupBox("📡 传感器")
        sensor_layout = QGridLayout(sensor_group)
        
        sensor_layout.addWidget(QLabel("LiDAR:"), 0, 0)
        self.lidar_label = QLabel("360点")
        self.lidar_label.setStyleSheet("color: #7ee787;")
        sensor_layout.addWidget(self.lidar_label, 0, 1)
        
        sensor_layout.addWidget(QLabel("相机:"), 1, 0)
        self.camera_label = QLabel("无目标")
        self.camera_label.setStyleSheet("color: #7ee787;")
        sensor_layout.addWidget(self.camera_label, 1, 1)
        
        sensor_layout.addWidget(QLabel("IMU:"), 2, 0)
        self.imu_label = QLabel("正常")
        self.imu_label.setStyleSheet("color: #7ee787;")
        sensor_layout.addWidget(self.imu_label, 2, 1)
        
        sensor_layout.addWidget(QLabel("GPS:"), 3, 0)
        self.gps_label = QLabel("已定位")
        self.gps_label.setStyleSheet("color: #7ee787;")
        sensor_layout.addWidget(self.gps_label, 3, 1)
        
        right_layout.addWidget(sensor_group)
        
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        layout.addWidget(splitter)
    
    def start_simulation(self):
        """启动仿真"""
        self.simulator.start()
        self.log("仿真系统已启动")
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(100)
    
    def set_velocity(self, linear: float, angular: float):
        """设置速度"""
        self.simulator.set_velocity(linear, angular)
    
    def update_simulation(self):
        """更新仿真"""
        state = self.simulator.get_state()
        
        pose = state.get('pose', {})
        self.x_label.setText(f"{pose.get('x', 0):.2f}m")
        self.y_label.setText(f"{pose.get('y', 0):.2f}m")
        
        yaw_deg = math.degrees(pose.get('yaw', 0))
        self.yaw_label.setText(f"{yaw_deg:.0f}°")
        
        vel = state.get('velocity', {})
        v = vel.get('linear', 0)
        self.vel_label.setText(f"{v:.2f} m/s")
        
        battery = state.get('battery', 100)
        self.battery_label.setText(f"{battery:.0f}%")
        if battery < 20:
            self.battery_label.setStyleSheet("color: #f85149; font-weight: bold;")
        elif battery < 50:
            self.battery_label.setStyleSheet("color: #f0883e; font-weight: bold;")
        else:
            self.battery_label.setStyleSheet("color: #7ee787; font-weight: bold;")
        
        obstacles = state.get('obstacles', 0)
        self.obstacle_label.setText(str(obstacles))
        
        vis_data = self.simulator.get_visualization_data()
        self.map_view.drawMap(vis_data)
        
        self.left_bar.setText(f"{int(self.simulator.physics.state.left_track)}%")
        self.right_bar.setText(f"{int(self.simulator.physics.state.right_track)}%")
    
    def log(self, message: str):
        """添加日志"""
        import datetime
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{time_str}] {message}")
    
    def closeEvent(self, event):
        """关闭事件"""
        self.simulator.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = RayMindSimGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
