#!/usr/bin/env python3
"""
RayMind OS - Qt控制界面
需要安装: pip install PyQt5
"""
import sys
import os
import math
import random
import time

def main():
    try:
        from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                     QHBoxLayout, QGridLayout, QLabel, QPushButton, 
                                     QGroupBox, QListWidget, QTextEdit, QProgressBar)
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal
        from PyQt5.QtGui import QPalette, QColor, QFont, QPainter, QPen, QBrush, QRadialGradient, QPolygonF
    except ImportError:
        print("""
❌ 缺少PyQt5依赖

请先安装:
    pip install PyQt5

或者运行Web版本:
    python3 raymind/web_gui.py
    访问: http://localhost:8080
""")
        sys.exit(1)


    class RobotCore:
        def __init__(self):
            self.state = "idle"
            self.position = {"x": 0.0, "y": 0.0, "yaw": 0.0}
            self.battery = 100.0
            self.targets = []
            self.running = False
        
        def start(self):
            self.running = True
            self.state = "ready"
            return True
        
        def stop(self):
            self.running = False
            self.state = "idle"
            return True
        
        def navigate_to(self, x, y):
            if self.state != "ready":
                return False
            self.state = "navigating"
            dx = x - self.position["x"]
            dy = y - self.position["y"]
            dist = math.sqrt(dx**2 + dy**2)
            time.sleep(min(dist * 0.3, 1.5))
            self.position["x"] = x
            self.position["y"] = y
            self.state = "ready"
            return True
        
        def scan(self, duration=3):
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
                self.navigate_to(t.get("x", 0), t.get("y", 0))
                time.sleep(0.3)
                count += 1
            self.state = "ready"
            return count
        
        def patrol(self, waypoints):
            self.state = "navigating"
            for wp in waypoints:
                self.navigate_to(wp.get("x", 0), wp.get("y", 0))
            self.state = "ready"
            return True


    class MapWidget(QWidget):
        robotPositionChanged = pyqtSignal(float, float)
        
        def __init__(self):
            super().__init__()
            self.setMinimumSize(600, 500)
            self.map_size = 10
            self.robot_x = 0
            self.robot_y = 0
            self.robot_yaw = 0
            self.targets = []
            self.waypoints = []
        
        def setRobotPosition(self, x, y, yaw=0):
            self.robot_x = x
            self.robot_y = y
            self.robot_yaw = yaw
            self.update()
        
        def setTargets(self, targets):
            self.targets = targets
            self.update()
        
        def setWaypoints(self, waypoints):
            self.waypoints = waypoints
            self.update()
        
        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                rect = self.rect()
                x = ((event.x() / rect.width()) - 0.5) * self.map_size * 2
                y = -(event.y() / rect.height() * self.map_size * 2) + self.map_size
                self.robotPositionChanged.emit(x, y)
        
        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            rect = self.rect()
            painter.fillRect(rect, QColor(10, 22, 40))
            
            grid_color = QColor(15, 52, 96, 100)
            pen = QPen(grid_color)
            pen.setWidth(1)
            painter.setPen(pen)
            
            for i in range(11):
                x_pos = rect.width() * i / 10
                painter.drawLine(x_pos, 0, x_pos, rect.height())
                y_pos = rect.height() * i / 10
                painter.drawLine(0, y_pos, rect.width(), y_pos)
            
            pen = QPen(QColor(0, 255, 136, 150))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(int(rect.width()/2), 0, int(rect.width()/2), int(rect.height()))
            painter.drawLine(0, int(rect.height()/2), int(rect.width()), int(rect.height()/2))
            
            for wp in self.waypoints:
                wx = (wp["x"] / self.map_size + 0.5) * rect.width()
                wy = (-wp["y"] / self.map_size + 0.5) * rect.height()
                painter.setBrush(QColor(255, 215, 0))
                painter.setPen(QPen(QColor(255, 215, 0)))
                painter.drawRect(int(wx-8), int(wy-8), 16, 16)
            
            for target in self.targets:
                tx = (target["x"] / self.map_size + 0.5) * rect.width()
                ty = (-target["y"] / self.map_size + 0.5) * rect.height()
                color = QColor(255, 71, 87)
                painter.setBrush(color)
                painter.setPen(QPen(color))
                painter.drawEllipse(int(tx-12), int(ty-12), 24, 24)
                conf = target.get("confidence", 0.8)
                text_color = QColor(0, 255, 136) if conf > 0.8 else QColor(255, 215, 0)
                painter.setPen(text_color)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(int(tx+15), int(ty), "{:.0%}".format(conf))
            
            rx = (self.robot_x / self.map_size + 0.5) * rect.width()
            ry = (-self.robot_y / self.map_size + 0.5) * rect.height()
            
            painter.save()
            painter.translate(int(rx), int(ry))
            painter.rotate(-self.robot_yaw * 180 / math.pi)
            
            gradient = QRadialGradient(0, 0, 20)
            gradient.setColorAt(0, QColor(0, 255, 136))
            gradient.setColorAt(1, QColor(0, 200, 100, 100))
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(QColor(0, 255, 136), 2))
            painter.drawEllipse(0, 0, 20, 20)
            
            painter.setBrush(QColor(0, 255, 136))
            triangle = QPolygonF([(0, -30), (-8, -15), (8, -15)])
            painter.drawPolygon(triangle)
            painter.restore()


    class RayMindGUI(QMainWindow):
        def __init__(self):
            super().__init__()
            self.robot = RobotCore()
            self.initUI()
            self.startUpdateTimer()
            
        def initUI(self):
            self.setWindowTitle("RayMind 智能农田机器人控制系统")
            self.setGeometry(100, 100, 1200, 700)
            self.setStyleSheet("""
                QMainWindow { background-color: #1a1a2e; }
                QLabel { color: #ffffff; }
                QPushButton {
                    background-color: #e94560; color: white; border: none;
                    padding: 10px; border-radius: 5px; font-weight: bold;
                }
                QPushButton:hover { background-color: #ff6b8a; }
                QPushButton#btnSuccess { background-color: #00ff88; color: #1a1a2e; }
                QPushButton#btnWarning { background-color: #ffd700; color: #1a1a2e; }
                QPushButton#btnDanger { background-color: #ff4757; }
                QGroupBox { color: #e94560; border: 2px solid #e94560; border-radius: 10px; }
                QTextEdit, QListWidget { background-color: #0a1628; color: #00ff88; border: 1px solid #0f3460; }
            """)
            
            central = QWidget()
            self.setCentralWidget(central)
            layout = QHBoxLayout(central)
            
            left_panel = QWidget()
            left_layout = QVBoxLayout(left_panel)
            
            map_label = QLabel("🗺️ 农田地图 (点击设置目标点)")
            map_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e94560;")
            left_layout.addWidget(map_label)
            
            self.map_widget = MapWidget()
            self.map_widget.robotPositionChanged.connect(self.onMapClick)
            left_layout.addWidget(self.map_widget)
            
            self.progress_bar = QProgressBar()
            left_layout.addWidget(self.progress_bar)
            
            self.task_status_label = QLabel("等待任务...")
            self.task_status_label.setStyleSheet("font-size: 14px; color: #ffd700;")
            left_layout.addWidget(self.task_status_label)
            
            layout.addWidget(left_panel, 3)
            
            right_panel = QWidget()
            right_layout = QVBoxLayout(right_panel)
            
            title = QLabel("🌾 RayMind 控制台")
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e94560; padding: 15px; background: #0f3460; border-radius: 10px;")
            title.setAlignment(Qt.AlignCenter)
            right_layout.addWidget(title)
            
            status_group = QGroupBox("📱 机器人状态")
            status_layout = QGridLayout(status_group)
            self.state_label = QLabel("IDLE")
            self.state_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
            status_layout.addWidget(QLabel("状态:"), 0, 0)
            status_layout.addWidget(self.state_label, 0, 1)
            self.battery_label = QLabel("100%")
            self.battery_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #00ff88;")
            status_layout.addWidget(QLabel("电量:"), 1, 0)
            status_layout.addWidget(self.battery_label, 1, 1)
            self.pos_x_label = QLabel("0.0")
            status_layout.addWidget(QLabel("X坐标:"), 2, 0)
            status_layout.addWidget(self.pos_x_label, 2, 1)
            self.pos_y_label = QLabel("0.0")
            status_layout.addWidget(QLabel("Y坐标:"), 3, 0)
            status_layout.addWidget(self.pos_y_label, 3, 1)
            right_layout.addWidget(status_group)
            
            control_group = QGroupBox("🎮 控制面板")
            control_layout = QVBoxLayout(control_group)
            btn_start = QPushButton("🚀 启动机器人")
            btn_start.setObjectName("btnSuccess")
            btn_start.clicked.connect(self.onStart)
            control_layout.addWidget(btn_start)
            btn_scan = QPushButton("🔍 扫描杂草")
            btn_scan.setObjectName("btnWarning")
            btn_scan.clicked.connect(self.onScan)
            control_layout.addWidget(btn_scan)
            btn_eradicate = QPushButton("💥 清除杂草")
            btn_eradicate.setObjectName("btnDanger")
            btn_eradicate.clicked.connect(self.onEradicate)
            control_layout.addWidget(btn_eradicate)
            btn_patrol = QPushButton("🚶 巡逻任务")
            btn_patrol.clicked.connect(self.onPatrol)
            control_layout.addWidget(btn_patrol)
            btn_stop = QPushButton("🛑 紧急停止")
            btn_stop.setObjectName("btnDanger")
            btn_stop.clicked.connect(self.onStop)
            control_layout.addWidget(btn_stop)
            right_layout.addWidget(control_group)
            
            target_group = QGroupBox("🎯 检测目标")
            target_layout = QVBoxLayout(target_group)
            self.target_list = QListWidget()
            target_layout.addWidget(self.target_list)
            right_layout.addWidget(target_group)
            
            log_group = QGroupBox("📝 操作日志")
            log_layout = QVBoxLayout(log_group)
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMaximumHeight(150)
            log_layout.addWidget(self.log_area)
            right_layout.addWidget(log_group)
            
            layout.addWidget(right_panel, 2)
            self.log("RayMind控制系统已启动")
        
        def startUpdateTimer(self):
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateStatus)
            self.timer.start(500)
        
        def updateStatus(self):
            self.state_label.setText(self.robot.state.upper())
            self.battery_label.setText("{:.0f}%".format(self.robot.battery))
            self.pos_x_label.setText("{:.1f}".format(self.robot.position["x"]))
            self.pos_y_label.setText("{:.1f}".format(self.robot.position["y"]))
            self.map_widget.setRobotPosition(self.robot.position["x"], self.robot.position["y"], self.robot.position.get("yaw", 0))
        
        def onMapClick(self, x, y):
            self.log("导航到目标点 ({:.1f}, {:.1f})".format(x, y))
            self.robot.navigate_to(x, y)
            self.task_status_label.setText("已导航到 ({:.1f}, {:.1f})".format(x, y))
        
        def onStart(self):
            self.robot.start()
            self.log("机器人已启动")
        
        def onScan(self):
            self.log("开始扫描...")
            self.task_status_label.setText("正在扫描...")
            self.progress_bar.setRange(0, 0)
            targets = self.robot.scan(duration=3)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.target_list.clear()
            for t in targets:
                self.target_list.addItem("目标 {}: {} - 置信度 {:.0%}".format(t["id"], t["type"], t["confidence"]))
            self.map_widget.setTargets(targets)
            self.log("扫描完成，发现 {} 个目标".format(len(targets)))
            self.task_status_label.setText("发现 {} 个目标".format(len(targets)))
            QTimer.singleShot(2000, lambda: self.progress_bar.setValue(0))
        
        def onEradicate(self):
            if not self.robot.targets:
                self.log("无目标可清除，请先扫描")
                return
            self.log("开始清除 {} 个目标...".format(len(self.robot.targets)))
            self.task_status_label.setText("正在清除目标...")
            count = self.robot.eradicate()
            self.robot.targets = []
            self.target_list.clear()
            self.map_widget.setTargets([])
            self.log("清除完成，已清除 {} 个目标".format(count))
            self.task_status_label.setText("已清除 {} 个目标".format(count))
        
        def onPatrol(self):
            self.log("开始巡逻任务...")
            self.task_status_label.setText("正在巡逻...")
            waypoints = [{"x": -4, "y": -4}, {"x": 4, "y": -4}, {"x": 4, "y": 4}, {"x": -4, "y": 4}]
            self.map_widget.setWaypoints(waypoints)
            self.robot.patrol(waypoints)
            self.map_widget.setWaypoints([])
            self.log("巡逻完成")
            self.task_status_label.setText("巡逻完成")
        
        def onStop(self):
            self.robot.stop()
            self.log("紧急停止!")
            self.task_status_label.setText("已停止")
        
        def log(self, message):
            timestamp = time.strftime("%H:%M:%S")
            self.log_area.append("[{}] {}".format(timestamp, message))
            self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())


    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(26, 26, 46))
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)
    window = RayMindGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
