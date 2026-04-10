#!/usr/bin/env python3
"""
网络通信模块 - RayMind Robot
支持 WiFi / 5G / 4G 网络连接
"""

import os
import sys
import socket
import threading
import time
import json
import logging
from typing import Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NetworkType(Enum):
    """网络类型"""
    WIFI = "wifi"
    ETHERNET = "ethernet"
    CELLULAR_5G = "5g"
    CELLULAR_4G = "4g"
    NONE = "none"


@dataclass
class NetworkStatus:
    """网络状态"""
    connected: bool
    network_type: NetworkType
    ip_address: str
    signal_strength: int = 0
    latency_ms: float = 0
    bandwidth_mbps: float = 0


class WiFiManager:
    """WiFi管理器"""
    
    def __init__(self):
        self.interface = "wlan0"
        self.connected = False
        self.ssid = None
        self.ip_address = None
        self.signal_strength = 0
    
    def scan_networks(self) -> list:
        """扫描WiFi网络"""
        try:
            result = os.popen(f"sudo iwlist {self.interface} scan 2>/dev/null | grep -i ssid").read()
            networks = []
            for line in result.split('\n'):
                if 'ESSID' in line:
                    ssid = line.split(':')[1].strip('"')
                    if ssid:
                        networks.append(ssid)
            return networks
        except Exception as e:
            logger.warning(f"WiFi scan failed: {e}")
            return []
    
    def connect(self, ssid: str, password: str = None) -> bool:
        """连接到WiFi网络"""
        try:
            if password:
                cmd = f"nmcli device wifi connect '{ssid}' password '{password}'"
            else:
                cmd = f"nmcli device wifi connect '{ssid}'"
            
            result = os.system(cmd)
            if result == 0:
                self.ssid = ssid
                self.connected = True
                self.ip_address = self._get_ip_address()
                logger.info(f"Connected to WiFi: {ssid}")
                return True
        except Exception as e:
            logger.error(f"WiFi connection failed: {e}")
        return False
    
    def disconnect(self) -> bool:
        """断开WiFi"""
        try:
            os.system(f"nmcli device disconnect {self.interface}")
            self.connected = False
            self.ssid = None
            return True
        except:
            return False
    
    def get_status(self) -> NetworkStatus:
        """获取WiFi状态"""
        self.connected = self._check_connection()
        if self.connected:
            self.ip_address = self._get_ip_address()
            self.signal_strength = self._get_signal_strength()
        
        return NetworkStatus(
            connected=self.connected,
            network_type=NetworkType.WIFI,
            ip_address=self.ip_address or "N/A",
            signal_strength=self.signal_strength
        )
    
    def _check_connection(self) -> bool:
        try:
            result = os.popen(f"iwconfig {self.interface} 2>/dev/null").read()
            return "ESSID" in result and "not-connected" not in result
        except:
            return False
    
    def _get_ip_address(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
    
    def _get_signal_strength(self) -> int:
        try:
            result = os.popen(f"iwconfig {self.interface} 2>/dev/null | grep -i signal").read()
            if 'Signal' in result:
                for part in result.split():
                    if 'Signal' in part:
                        idx = result.index(part)
                        return int(result[idx:].split()[1].replace('=', '').replace('dBm', '').strip())
        except:
            pass
        return 0


class CellularManager:
    """5G/4G蜂窝网络管理器"""
    
    def __init__(self):
        self.interface = "wwan0"
        self.connected = False
        self.network_type = NetworkType.NONE
        self.ip_address = None
        self.signal_strength = 0
        self.operator = None
        self.modem_available = False
    
    def detect_modem(self) -> bool:
        """检测5G/4G模块"""
        modem_paths = [
            "/dev/ttyUSB0",
            "/dev/ttyUSB1", 
            "/dev/ttyUSB2",
            "/dev/ttyACM0",
            "/dev/ttyACM1"
        ]
        
        for path in modem_paths:
            if os.path.exists(path):
                self.modem_available = True
                logger.info(f"Modem detected at {path}")
                return True
        
        logger.warning("No cellular modem detected")
        return False
    
    def connect(self, apn: str = "internet") -> bool:
        """连接到蜂窝网络"""
        if not self.modem_available:
            self.detect_modem()
        
        try:
            os.system(f"mmcli -m 0 --simple-connect='apn={apn}' 2>/dev/null")
            time.sleep(2)
            
            self.connected = True
            self.network_type = self._detect_network_type()
            self.ip_address = self._get_ip_address()
            self.operator = self._get_operator()
            
            logger.info(f"Connected to cellular: {self.network_type.value}")
            return True
        except Exception as e:
            logger.error(f"Cellular connection failed: {e}")
        
        return False
    
    def disconnect(self) -> bool:
        """断开蜂窝网络"""
        try:
            os.system("mmcli -m 0 --simple-disconnect 2>/dev/null")
            self.connected = False
            return True
        except:
            return False
    
    def get_status(self) -> NetworkStatus:
        """获取蜂窝网络状态"""
        if self.connected:
            self.signal_strength = self._get_signal_strength()
            self.network_type = self._detect_network_type()
        
        return NetworkStatus(
            connected=self.connected,
            network_type=self.network_type,
            ip_address=self.ip_address or "N/A",
            signal_strength=self.signal_strength
        )
    
    def _detect_network_type(self) -> NetworkType:
        try:
            result = os.popen("mmcli -m 0 --output-json 2>/dev/null").read()
            data = json.loads(result)
            tech = data.get('modem', {}).get('accesstechnologies', '')
            
            if '5G' in tech:
                return NetworkType.CELLULAR_5G
            elif 'LTE' in tech or '4G' in tech:
                return NetworkType.CELLULAR_4G
        except:
            pass
        return NetworkType.CELLULAR_4G
    
    def _get_signal_strength(self) -> int:
        try:
            result = os.popen("mmcli -m 0 --output-json 2>/dev/null").read()
            data = json.loads(result)
            return data.get('modem', {}).get('signalquality', {}).get('recent', 0)
        except:
            return 0
    
    def _get_operator(self) -> Optional[str]:
        try:
            result = os.popen("mmcli -m 0 --output-json 2>/dev/null").read()
            data = json.loads(result)
            return data.get('modem', {}).get('operator', {}).get('name', 'Unknown')
        except:
            return None
    
    def _get_ip_address(self) -> Optional[str]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None


class NetworkRelay:
    """网络透传模块 - 实现远程控制"""
    
    def __init__(self, server_host: str = None, server_port: int = 8888):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.receive_callback = None
        self.running = False
    
    def start_server(self, port: int = 8888):
        """启动服务器（机器人端）"""
        self.server_port = port
        self.running = True
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(1)
        
        logger.info(f"Network relay server started on port {port}")
        
        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                logger.info(f"Client connected: {addr}")
                self.socket = client_socket
                self.connected = True
                
                threading.Thread(target=self._receive_loop, daemon=True).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Server error: {e}")
    
    def connect(self, host: str, port: int = 8888):
        """连接到服务器（控制端）"""
        self.server_host = host
        self.server_port = port
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.connected = True
        logger.info(f"Connected to relay server: {host}:{port}")
        
        threading.Thread(target=self._receive_loop, daemon=True).start()
    
    def send(self, data: dict):
        """发送数据"""
        if self.connected and self.socket:
            try:
                msg = json.dumps(data).encode('utf-8')
                self.socket.sendall(len(msg).to_bytes(4, 'big'))
                self.socket.sendall(msg)
            except Exception as e:
                logger.error(f"Send failed: {e}")
                self.connected = False
    
    def send_cmd(self, cmd: str, params: dict = None):
        """发送控制命令"""
        data = {
            "type": "cmd",
            "cmd": cmd,
            "params": params or {}
        }
        self.send(data)
    
    def send_telemetry(self, data: dict):
        """发送遥测数据"""
        msg = {
            "type": "telemetry",
            "data": data
        }
        self.send(msg)
    
    def set_receive_callback(self, callback: Callable):
        """设置接收回调"""
        self.receive_callback = callback
    
    def _receive_loop(self):
        """接收数据循环"""
        while self.running and self.connected:
            try:
                header = self.socket.recv(4)
                if not header:
                    break
                
                length = int.from_bytes(header, 'big')
                data = b''
                
                while len(data) < length:
                    chunk = self.socket.recv(length - len(data))
                    if not chunk:
                        break
                    data += chunk
                
                if data and self.receive_callback:
                    msg = json.loads(data.decode('utf-8'))
                    self.receive_callback(msg)
                    
            except Exception as e:
                logger.error(f"Receive error: {e}")
                break
        
        self.connected = False
        logger.info("Connection closed")
    
    def close(self):
        """关闭连接"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        self.connected = False


class NetworkManager:
    """综合网络管理器"""
    
    def __init__(self):
        self.wifi = WiFiManager()
        self.cellular = CellularManager()
        self.relay = NetworkRelay()
        self.primary_network = NetworkType.NONE
    
    def get_status(self) -> NetworkStatus:
        """获取网络状态"""
        wifi_status = self.wifi.get_status()
        if wifi_status.connected:
            self.primary_network = NetworkType.WIFI
            return wifi_status
        
        cellular_status = self.cellular.get_status()
        if cellular_status.connected:
            self.primary_network = cellular_status.network_type
            return cellular_status
        
        return NetworkStatus(
            connected=False,
            network_type=NetworkType.NONE,
            ip_address="N/A"
        )
    
    def start_relay_server(self, port: int = 8888):
        """启动网络透传服务器"""
        threading.Thread(target=self.relay.start_server, args=(port,), daemon=True).start()
    
    def connect_to_relay(self, host: str, port: int = 8888):
        """连接到透传服务器"""
        self.relay.connect(host, port)


if __name__ == '__main__':
    print("Network Module for RayMind")
    print("=" * 40)
    
    manager = NetworkManager()
    status = manager.get_status()
    
    print(f"Connected: {status.connected}")
    print(f"Type: {status.network_type.value}")
    print(f"IP: {status.ip_address}")
    print(f"Signal: {status.signal_strength}")
    
    print("\nUsage:")
    print("  from network import NetworkManager")
    print("  manager = NetworkManager()")
    print("  manager.wifi.connect('SSID', 'password')")
    print("  manager.cellular.connect('internet')")
    print("  manager.relay.connect('192.168.1.100', 8888)")
