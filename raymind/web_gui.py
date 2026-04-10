#!/usr/bin/env python3
"""
RayMind OS - Web可视化控制界面
"""
import sys
sys.path.insert(0, '/home/meta/RayMind')

from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import json
import time
import os

class FarmRobot:
    def __init__(self, model_path="best.pt"):
        self.state = "idle"
        self.position = {"x": 0.0, "y": 0.0, "yaw": 0.0}
        self.battery = 100.0
        self.model_path = model_path
        self.targets = []
        
    def start(self):
        print("正在初始化RayMind机器人...")
        time.sleep(0.3)
        self.state = "ready"
        print(f"机器人就绪 | 位置: ({self.position['x']}, {self.position['y']})")
        return True
    
    def stop(self):
        self.state = "idle"
        return True
    
    def get_status(self):
        return {
            "state": self.state,
            "position": self.position,
            "battery": self.battery
        }
    
    def navigate_to(self, x, y):
        if self.state != "ready":
            return False
        self.state = "navigating"
        import math
        dx = x - self.position["x"]
        dy = y - self.position["y"]
        dist = math.sqrt(dx**2 + dy**2)
        time.sleep(min(dist * 0.3, 1.5))
        self.position["x"] = x
        self.position["y"] = y
        self.state = "ready"
        return True
    
    def scan(self, duration=5):
        if self.state != "ready":
            return []
        self.state = "scanning"
        time.sleep(duration)
        import random
        num = random.randint(3, 8)
        self.targets = []
        for i in range(num):
            self.targets.append({
                "id": i+1,
                "x": random.uniform(-4, 4),
                "y": random.uniform(-4, 4),
                "type": "weed",
                "confidence": random.uniform(0.6, 0.99)
            })
        self.state = "ready"
        return self.targets
    
    def get_targets(self):
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


HTML_CONTENT = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RayMind 智能农田机器人控制台</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh; color: #fff;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            text-align: center; padding: 30px 0;
            background: linear-gradient(90deg, #0f3460, #e94560);
            border-radius: 15px; margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        h1 { font-size: 2.5em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .subtitle { color: #ffd700; margin-top: 10px; }
        .main-grid { display: grid; grid-template-columns: 1fr 350px; gap: 20px; }
        .panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px; padding: 20px;
            backdrop-filter: blur(10px);
        }
        .panel h2 {
            border-bottom: 2px solid #e94560;
            padding-bottom: 10px; margin-bottom: 15px; color: #e94560;
        }
        #map {
            width: 100%; height: 450px;
            background: #0a1628;
            border-radius: 10px; position: relative;
            overflow: hidden; border: 2px solid #0f3460;
            cursor: crosshair;
        }
        .grid-line { position: absolute; background: rgba(15, 52, 96, 0.5); }
        #robot {
            position: absolute; width: 35px; height: 35px;
            background: #00ff88; border-radius: 50%;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 20px #00ff88;
            transition: all 0.3s ease; z-index: 10;
        }
        #robot::after {
            content: ''; position: absolute; top: -12px; left: 50%;
            transform: translateX(-50%);
            border-left: 8px solid transparent; border-right: 8px solid transparent;
            border-bottom: 15px solid #00ff88;
        }
        .target {
            position: absolute; width: 18px; height: 18px;
            background: #ff4757; border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: translate(-50%, -50%) scale(1); }
            50% { transform: translate(-50%, -50%) scale(1.3); }
        }
        .status-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .status-item {
            background: rgba(0,0,0,0.3); padding: 15px;
            border-radius: 10px; text-align: center;
        }
        .status-value { font-size: 1.6em; font-weight: bold; color: #00ff88; }
        .status-label { color: #aaa; font-size: 0.9em; }
        .btn {
            width: 100%; padding: 12px; margin: 5px 0;
            border: none; border-radius: 8px;
            cursor: pointer; font-size: 1em;
            transition: all 0.3s; font-weight: bold;
        }
        .btn-primary { background: #e94560; color: white; }
        .btn-primary:hover { background: #ff6b8a; transform: translateY(-2px); }
        .btn-success { background: #00ff88; color: #1a1a2e; }
        .btn-success:hover { background: #66ffaa; }
        .btn-warning { background: #ffd700; color: #1a1a2e; }
        .btn-danger { background: #ff4757; color: white; }
        .log-area {
            background: #0a1628; border-radius: 10px;
            padding: 10px; height: 180px;
            overflow-y: auto; font-family: monospace; font-size: 0.85em;
        }
        .log-item { padding: 5px 0; border-bottom: 1px solid #1a2a4a; }
        .progress-bar {
            width: 100%; height: 20px;
            background: #1a2a4a; border-radius: 10px;
            overflow: hidden; margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            transition: width 0.3s;
        }
        .target-list { max-height: 200px; overflow-y: auto; }
        .target-item {
            display: flex; justify-content: space-between;
            padding: 10px; background: rgba(0,0,0,0.2);
            margin: 5px 0; border-radius: 5px;
            border-left: 3px solid #ff4757;
        }
        .footer { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌾 RayMind 智能农田机器人</h1>
            <div class="subtitle">RayMind OS - 机器人控制系统</div>
        </header>
        
        <div class="main-grid">
            <div class="left-col">
                <div class="panel">
                    <h2>🗺️ 农田地图 (点击导航)</h2>
                    <div id="map">
                        <div class="grid-line" style="width:100%;height:1px;top:50%;left:0;"></div>
                        <div class="grid-line" style="width:1px;height:100%;top:0;left:50%;"></div>
                        <div id="robot" style="left:50%;top:50%;"></div>
                    </div>
                </div>
                
                <div class="panel" style="margin-top:20px;">
                    <h2>📊 任务进度</h2>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progress" style="width:0%"></div>
                    </div>
                    <div id="task-status">等待任务...</div>
                </div>
            </div>
            
            <div class="right-col">
                <div class="panel">
                    <h2>📱 机器人状态</h2>
                    <div class="status-grid">
                        <div class="status-item">
                            <div class="status-value" id="state">--</div>
                            <div class="status-label">状态</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="battery">--</div>
                            <div class="status-label">电量</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="pos-x">0.0</div>
                            <div class="status-label">X坐标</div>
                        </div>
                        <div class="status-item">
                            <div class="status-value" id="pos-y">0.0</div>
                            <div class="status-label">Y坐标</div>
                        </div>
                    </div>
                </div>
                
                <div class="panel" style="margin-top:20px;">
                    <h2>🎮 控制面板</h2>
                    <button class="btn btn-success" onclick="startRobot()">🚀 启动</button>
                    <button class="btn btn-warning" onclick="scanTargets()">🔍 扫描杂草</button>
                    <button class="btn btn-danger" onclick="eradicateAll()">💥 清除杂草</button>
                    <button class="btn btn-primary" onclick="startPatrol()">🚶 巡逻</button>
                    <button class="btn btn-danger" onclick="emergencyStop()">🛑 停止</button>
                </div>
                
                <div class="panel" style="margin-top:20px;">
                    <h2>🎯 目标列表</h2>
                    <div class="target-list" id="target-list">
                        <div style="text-align:center;color:#666;padding:20px;">暂无目标</div>
                    </div>
                </div>
                
                <div class="panel" style="margin-top:20px;">
                    <h2>📝 日志</h2>
                    <div class="log-area" id="log-area"></div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            🤖 RayMind OS v1.0 | 深度感知 · 自主导航 · 杂草识别 · 激光打击
        </div>
    </div>
    
    <script>
        const MAP_SIZE = 10;
        let targets = [];
        
        function log(msg) {
            const area = document.getElementById('log-area');
            const time = new Date().toLocaleTimeString();
            area.innerHTML = `<div class="log-item">[${time}] ${msg}</div>` + area.innerHTML;
        }
        
        function updateStatus() {
            fetch('/api/status').then(r=>r.json()).then(data => {
                document.getElementById('state').textContent = data.state.toUpperCase();
                document.getElementById('battery').textContent = data.battery + '%';
                document.getElementById('pos-x').textContent = data.position.x.toFixed(1);
                document.getElementById('pos-y').textContent = data.position.y.toFixed(1);
                
                const robot = document.getElementById('robot');
                const x = 50 + (data.position.x / MAP_SIZE) * 45;
                const y = 50 - (data.position.y / MAP_SIZE) * 45;
                robot.style.left = x + '%';
                robot.style.top = y + '%';
            });
            
            fetch('/api/targets').then(r=>r.json()).then(data => {
                targets = data.targets;
                renderTargets();
            });
            
            setTimeout(updateStatus, 500);
        }
        
        function renderTargets() {
            const list = document.getElementById('target-list');
            const map = document.getElementById('map');
            map.querySelectorAll('.target').forEach(e=>e.remove());
            
            if (targets.length === 0) {
                list.innerHTML = '<div style="text-align:center;color:#666;padding:20px;">暂无目标</div>';
                return;
            }
            
            let html = '';
            targets.forEach((t, i) => {
                html += `<div class="target-item">
                    <span>目标 ${i+1}: ${t.type}</span>
                    <span style="color:${t.confidence > 0.8 ? '#00ff88' : '#ffd700'}">${(t.confidence*100).toFixed(0)}%</span>
                </div>`;
                
                const tx = 50 + (t.x / MAP_SIZE) * 45;
                const ty = 50 - (t.y / MAP_SIZE) * 45;
                const marker = document.createElement('div');
                marker.className = 'target';
                marker.style.left = tx + '%';
                marker.style.top = ty + '%';
                map.appendChild(marker);
            });
            list.innerHTML = html;
        }
        
        function startRobot() {
            log('启动RayMind机器人...');
            fetch('/api/start', {method:'POST'}).then(r=>r.json()).then(d => {
                if(d.success) log('机器人已就绪');
            });
        }
        
        function scanTargets() {
            log('开始扫描...');
            fetch('/api/scan?duration=3', {method:'POST'}).then(r=>r.json()).then(d => {
                log(`发现 ${d.targets.length} 个目标`);
                document.getElementById('task-status').textContent = `发现 ${d.targets.length} 个目标`;
                document.getElementById('progress').style.width = '100%';
                setTimeout(()=>document.getElementById('progress').style.width = '0%', 2000);
            });
        }
        
        function eradicateAll() {
            if (targets.length === 0) { log('无目标可清除'); return; }
            log(`清除 ${targets.length} 个目标...`);
            fetch('/api/eradicate', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({targets:targets})
            }).then(r=>r.json()).then(d => {
                log(`清除完成: ${d.eradicated} 个`);
                targets = [];
                renderTargets();
            });
        }
        
        function startPatrol() {
            log('开始巡逻...');
            fetch('/api/patrol', {method:'POST'}).then(r=>r.json()).then(d => {
                log('巡逻完成');
            });
        }
        
        function emergencyStop() {
            log('停止!');
            fetch('/api/stop', {method:'POST'});
        }
        
        document.getElementById('map').addEventListener('click', function(e) {
            const rect = this.getBoundingClientRect();
            const x = ((e.clientX - rect.left) / rect.width - 0.5) * MAP_SIZE * 2;
            const y = -(e.clientY - rect.top) / rect.height * MAP_SIZE * 2 + MAP_SIZE;
            log(`导航到 (${x.toFixed(1)}, ${y.toFixed(1)})`);
            fetch('/api/navigate', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({x:x, y:y})
            });
        });
        
        log('RayMind控制台已连接');
        updateStatus();
    </script>
</body>
</html>'''


class RobotHandler(SimpleHTTPRequestHandler):
    robot = None
    
    def do_GET(self):
        if self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(self.robot.get_status()).encode())
        elif self.path == '/api/targets':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'targets': self.robot.get_targets()}).encode())
        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/start':
            self.robot.start()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif self.path == '/api/stop':
            self.robot.stop()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif self.path.startswith('/api/scan'):
            targets = self.robot.scan(duration=3)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'targets': targets}).encode())
        elif self.path == '/api/eradicate':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            count = self.robot.eradicate(data.get('targets', []))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True, 'eradicated': count}).encode())
        elif self.path == '/api/patrol':
            waypoints = [{"x":-4,"y":-4},{"x":4,"y":-4},{"x":4,"y":4},{"x":-4,"y":4}]
            self.robot.patrol(waypoints)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')
        elif self.path == '/api/navigate':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            self.robot.navigate_to(data.get('x', 0), data.get('y', 0))
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"success":true}')


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║       🌾 RayMind 智能农田机器人 - 可视化控制界面 🌾            ║
╠══════════════════════════════════════════════════════════════╣
║  🎮 打开浏览器访问:  http://localhost:8080                    ║
║                                                              ║
║  功能:                                                       ║
║  • 点击地图进行导航                                           ║
║  • 扫描识别杂草                                               ║
║  • 激光清除杂草                                               ║
║  • 自主巡逻                                                   ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    RobotHandler.robot = FarmRobot()
    RobotHandler.robot.start()
    
    server = HTTPServer(('0.0.0.0', 8080), RobotHandler)
    print("服务器运行中... 按 Ctrl+C 停止")
    server.serve_forever()


if __name__ == '__main__':
    main()
