#!/usr/bin/env python3
"""
电池管理模块 - RayMind Robot
支持电压检测、电流检测、电量计算、充电状态
"""

import os
import sys
import time
import threading
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BatteryData:
    """电池数据"""
    voltage: float = 0.0
    current: float = 0.0
    percentage: float = 100.0
    temperature: float = 25.0
    capacity: float = 20.0
    remaining: float = 20.0
    status: str = "discharging"
    health: float = 100.0
    estimated_time: int = 0


class BatteryMonitor:
    """电池监控器"""
    
    def __init__(self, 
                 nominal_voltage: float = 48.0,
                 capacity_ah: float = 20.0,
                 cell_count: int = 12):
        self.nominal_voltage = nominal_voltage
        self.capacity_ah = capacity_ah
        self.cell_count = cell_count
        self.max_voltage = 4.2 * cell_count
        self.min_voltage = 3.0 * cell_count
        
        self.battery_data = BatteryData()
        self.monitoring = False
        self.monitor_thread = None
        
        self.adc_enabled = False
        self.i2c_enabled = False
        
        self._init_hardware()
    
    def _init_hardware(self):
        """初始化硬件接口"""
        self._try_init_adc()
        self._try_init_i2c()
    
    def _try_init_adc(self):
        """尝试初始化ADC"""
        try:
            import smbus2
            self.adc = smbus2.SMBus(1)
            self.adc_enabled = True
            logger.info("ADC initialized via I2C")
        except ImportError:
            logger.warning("smbus2 not installed")
        except Exception as e:
            logger.warning(f"ADC init failed: {e}")
    
    def _try_init_i2c(self):
        """尝试初始化I2C电池管理芯片"""
        try:
            import smbus2
            self.i2c = smbus2.SMBus(1)
            
            self.i2c_addresses = [0x36, 0x62, 0x64]
            for addr in self.i2c_addresses:
                try:
                    self.i2c.read_word_data(addr, 0x00)
                    self.battery_addr = addr
                    self.i2c_enabled = True
                    logger.info(f"Battery IC found at 0x{addr:02x}")
                    break
                except:
                    continue
            
            if not self.i2c_enabled:
                logger.warning("No battery IC found on I2C")
        except ImportError:
            logger.warning("smbus2 not installed for battery")
        except Exception as e:
            logger.warning(f"I2C init failed: {e}")
    
    def start_monitoring(self):
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Battery monitoring started")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Battery monitoring stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            self.update()
            time.sleep(1.0)
    
    def update(self) -> BatteryData:
        """更新电池数据"""
        if self.i2c_enabled:
            self._read_from_i2c()
        elif self.adc_enabled:
            self._read_from_adc()
        else:
            self._simulate_battery()
        
        self._calculate_percentage()
        
        return self.battery_data
    
    def _read_from_i2c(self):
        """从I2C电池管理芯片读取"""
        try:
            addr = self.battery_addr
            
            voltage_raw = self.i2c.read_word_data(addr, 0x09)
            voltage = (voltage_raw & 0xFF) << 8 | (voltage_raw >> 8)
            voltage = voltage * 1.25 / 1000.0 / 16.0
            self.battery_data.voltage = voltage
            
            current_raw = self.i2c.read_word_data(addr, 0x0A)
            current = (current_raw & 0xFF) << 8 | (current_raw >> 8)
            if current > 32767:
                current -= 65536
            current = current * 0.625 / 50.0
            self.battery_data.current = current
            
            percentage_raw = self.i2c.read_word_data(addr, 0x06)
            self.battery_data.percentage = (percentage_raw >> 8) & 0xFF
            
            temp_raw = self.i2c.read_word_data(addr, 0x08)
            self.battery_data.temperature = (temp_raw >> 8) & 0xFF
            
        except Exception as e:
            logger.warning(f"I2C read error: {e}")
            self._simulate_battery()
    
    def _read_from_adc(self):
        """从ADC读取"""
        try:
            voltage_ratio = self.adc.read_adc_voltage(0) / 5.0
            self.battery_data.voltage = voltage_ratio * (self.max_voltage / 3.3)
            
            current_ratio = self.adc.read_adc_voltage(1) / 5.0
            self.battery_data.current = (current_ratio - 0.5) * 20.0
            
        except Exception as e:
            logger.warning(f"ADC read error: {e}")
            self._simulate_battery()
    
    def _simulate_battery(self):
        """模拟电池数据（无硬件时）"""
        import random
        
        discharge_rate = 0.01
        self.battery_data.voltage = self.nominal_voltage - random.uniform(0, 1)
        
        if self.battery_data.percentage > 5:
            self.battery_data.current = -2.0 + random.uniform(-0.5, 0.5)
            self.battery_data.status = "discharging"
        else:
            self.battery_data.current = 0.5
            self.battery_data.status = "critical"
        
        self.battery_data.percentage -= discharge_rate
        self.battery_data.percentage = max(0, min(100, self.battery_data.percentage))
        
        self.battery_data.temperature = 25.0 + random.uniform(-2, 5)
        
        self.battery_data.remaining = self.capacity_ah * (self.battery_data.percentage / 100.0)
        
        if self.battery_data.current < 0:
            hours = self.battery_data.remaining / abs(self.battery_data.current)
            self.battery_data.estimated_time = int(hours * 60)
        else:
            remaining_capacity = self.capacity_ah - self.battery_data.remaining
            hours = remaining_capacity / self.battery_data.current
            self.battery_data.estimated_time = int(hours * 60)
    
    def _calculate_percentage(self):
        """计算电量百分比"""
        if self.battery_data.voltage > 0:
            voltage_range = self.max_voltage - self.min_voltage
            voltage_offset = self.battery_data.voltage - self.min_voltage
            percentage = (voltage_offset / voltage_range) * 100
            self.battery_data.percentage = max(0, min(100, percentage))
    
    def get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            "discharging": "放电中",
            "charging": "充电中",
            "critical": "电量不足",
            "full": "已充满",
            "idle": "待机"
        }
        return status_map.get(self.battery_data.status, "未知")
    
    def get_health_status(self) -> str:
        """获取健康状态"""
        if self.battery_data.health > 80:
            return "良好"
        elif self.battery_data.health > 50:
            return "一般"
        else:
            return "需更换"
    
    def is_low_battery(self) -> bool:
        """是否低电量"""
        return self.battery_data.percentage < 20
    
    def is_critical(self) -> bool:
        """是否严重不足"""
        return self.battery_data.percentage < 10
    
    def get_summary(self) -> Dict:
        """获取电池摘要"""
        return {
            "voltage": f"{self.battery_data.voltage:.1f}V",
            "current": f"{self.battery_data.current:.1f}A",
            "percentage": f"{self.battery_data.percentage:.0f}%",
            "status": self.get_status_text(),
            "time_remaining": self._format_time(self.battery_data.estimated_time),
            "temperature": f"{self.battery_data.temperature:.1f}°C",
            "health": self.get_health_status()
        }
    
    def _format_time(self, minutes: int) -> str:
        """格式化时间"""
        if minutes <= 0:
            return "--"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h{mins}m"


class SimulatedBattery:
    """模拟电池（纯软件）"""
    
    def __init__(self):
        self.percentage = 85.0
        self.voltage = 48.5
        self.current = -1.5
        self.temperature = 28.0
        self.status = "discharging"
    
    def update(self):
        """更新电池状态"""
        import random
        
        if self.percentage > 5:
            self.percentage -= 0.1
            self.current = -1.5 + random.uniform(-0.3, 0.3)
            self.status = "discharging"
        else:
            self.current = 0
            self.status = "critical"
        
        self.voltage = 42.0 + (self.percentage / 100) * 8.0
        self.temperature = 25 + random.uniform(0, 5)


if __name__ == '__main__':
    print("Battery Monitor Test")
    print("=" * 40)
    
    monitor = BatteryMonitor()
    monitor.start_monitoring()
    
    try:
        for i in range(10):
            data = monitor.update()
            print(f"{i+1}. 电量: {data.percentage:.1f}% | "
                  f"电压: {data.voltage:.1f}V | "
                  f"电流: {data.current:.1f}A | "
                  f"状态: {monitor.get_status_text()}")
            time.sleep(1)
    finally:
        monitor.stop_monitoring()
