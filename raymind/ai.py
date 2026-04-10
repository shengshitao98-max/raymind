#!/usr/bin/env python3
"""
RayMind OS - AI模块
集成YOLO模型进行杂草检测与识别
"""
import os
import sys
import time
import logging
import threading
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RayMindAI")


@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    center: Tuple[int, int]
    depth: float


@dataclass
class WeedDetection:
    position: Tuple[float, float]
    confidence: float
    weed_type: str
    size: float
    timestamp: float


class YOLOModel:
    """YOLO目标检测模型"""
    
    def __init__(self, model_path: str = "best.pt", conf_threshold: float = 0.5):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.model = None
        self.available = False
        self._load_model()
    
    def _load_model(self):
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA available, using GPU")
            
            try:
                from ultralytics import YOLO
                self.model = YOLO(self.model_path)
                self.available = True
                logger.info(f"YOLO model loaded: {self.model_path}")
            except ImportError:
                logger.warning("ultralytics not installed, using simulation")
                self._create_simulated_model()
                
        except ImportError:
            logger.warning("PyTorch not installed, using simulation")
            self._create_simulated_model()
    
    def _create_simulated_model(self):
        logger.info("Using simulated YOLO model for testing")
        self.available = True
    
    def detect(self, image) -> List[DetectionResult]:
        if not self.available:
            return []
        
        if self.model is not None:
            try:
                results = self.model(image, conf=self.conf_threshold, verbose=False)
                detections = []
                
                for r in results:
                    if r.boxes is not None:
                        for box in r.boxes:
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            conf = float(box.conf[0])
                            cls = int(box.cls[0])
                            
                            detections.append(DetectionResult(
                                class_name=r.names[cls],
                                confidence=conf,
                                bbox=(int(x1), int(y1), int(x2), int(y2)),
                                center=((int(x1)+int(x2))//2, (int(y1)+int(y2))//2),
                                depth=0.0
                            ))
                
                return detections
                
            except Exception as e:
                logger.error(f"Detection error: {e}")
        
        return self._simulate_detection(image)
    
    def _simulate_detection(self, image) -> List[DetectionResult]:
        import random
        detections = []
        num = random.randint(2, 6)
        
        for i in range(num):
            detections.append(DetectionResult(
                class_name="weed",
                confidence=random.uniform(0.5, 0.95),
                bbox=(random.randint(100, 500), random.randint(100, 300), 
                      random.randint(150, 600), random.randint(150, 400)),
                center=(random.randint(200, 500), random.randint(200, 400)),
                depth=random.uniform(0.5, 5.0)
            ))
        
        return detections
    
    def set_confidence(self, conf: float):
        self.conf_threshold = max(0.0, min(1.0, conf))


class DepthEstimator:
    """深度估计模块"""
    
    def __init__(self):
        self.focal_length = 525.0
        self.available = False
        self._init_estimator()
    
    def _init_estimator(self):
        try:
            import cv2
            self._cv2 = cv2
            self.available = True
            logger.info("Depth estimator initialized")
        except:
            logger.warning("OpenCV not available, using simulation")
    
    def estimate_depth(self, bbox: Tuple[int, int, int, int], 
                      known_height: float = 0.3) -> float:
        if not self.available:
            return 2.0
        
        try:
            _, y2, _, y1 = bbox
            pixel_height = y2 - y1
            if pixel_height > 0:
                depth = (known_height * self.focal_length) / pixel_height
                return max(0.3, min(10.0, depth))
        except:
            pass
        
        return 2.0


class WeedDetector:
    """杂草检测主模块"""
    
    def __init__(self, model_path: str = "best.pt"):
        self.yolo = YOLOModel(model_path)
        self.depth_estimator = DepthEstimator()
        self.confidence_threshold = 0.5
        self.detection_history: List[WeedDetection] = []
        self._running = False
        logger.info("Weed detector initialized")
    
    def detect_from_frame(self, frame) -> List[WeedDetection]:
        detections = self.yolo.detect(frame)
        
        results = []
        for det in detections:
            if det.confidence >= self.confidence_threshold:
                depth = self.depth_estimator.estimate_depth(det.bbox)
                
                det.depth = depth
                
                x_pixel, y_pixel = det.center
                world_x = (x_pixel - 320) * depth / self.focal_length
                world_y = depth
                
                result = WeedDetection(
                    position=(world_x, world_y),
                    confidence=det.confidence,
                    weed_type=det.class_name,
                    size=(det.bbox[2]-det.bbox[0]) * (det.bbox[3]-det.bbox[1]),
                    timestamp=time.time()
                )
                results.append(result)
        
        self.detection_history.extend(results)
        
        if len(self.detection_history) > 1000:
            self.detection_history = self.detection_history[-500:]
        
        return results
    
    def detect_from_camera(self, camera, duration: float = 5.0) -> List[WeedDetection]:
        self._running = True
        all_detections = []
        start_time = time.time()
        
        while time.time() - start_time < duration and self._running:
            frame = camera.capture()
            if frame and frame.data:
                detections = self.detect_from_frame(frame.data)
                all_detections.extend(detections)
            
            time.sleep(0.1)
        
        return all_detections
    
    def set_threshold(self, threshold: float):
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        self.yolo.set_confidence(threshold)
    
    def get_statistics(self) -> Dict:
        if not self.detection_history:
            return {"total": 0, "avg_confidence": 0.0}
        
        confidences = [d.confidence for d in self.detection_history]
        return {
            "total": len(self.detection_history),
            "avg_confidence": sum(confidences) / len(confidences),
            "high_confidence": len([c for c in confidences if c > 0.8]),
            "last_detection": self.detection_history[-1].timestamp if self.detection_history else 0
        }
    
    def stop(self):
        self._running = False


class NavigationAI:
    """导航AI模块 - 路径规划"""
    
    def __init__(self, grid_size: float = 0.5):
        self.grid_size = grid_size
        self.occupancy_grid = {}
        self.target_position = None
        logger.info("Navigation AI initialized")
    
    def update_map(self, lidar_points: List, robot_position: Tuple[float, float]):
        for point in lidar_points:
            x, y = point
            grid_x = int(x / self.grid_size)
            grid_y = int(y / self.grid_size)
            self.occupancy_grid[(grid_x, grid_y)] = 1
    
    def plan_path(self, start: Tuple[float, float], 
                  goal: Tuple[float, float]) -> List[Tuple[float, float]]:
        path = [start]
        
        dx = goal[0] - start[0]
        dy = goal[1] - start[1]
        steps = max(abs(dx), abs(dy)) / self.grid_size
        
        for i in range(int(steps)):
            t = (i + 1) / steps
            x = start[0] + dx * t
            y = start[1] + dy * t
            
            grid_x = int(x / self.grid_size)
            grid_y = int(y / self.grid_size)
            
            if self.occupancy_grid.get((grid_x, grid_y), 0) == 0:
                path.append((x, y))
        
        path.append(goal)
        return path
    
    def obstacle_avoidance(self, current_pos: Tuple[float, float],
                         desired_dir: Tuple[float, float],
                         lidar_data: List) -> Tuple[float, float]:
        min_distance = float('inf')
        obstacle_angle = 0
        
        for point in lidar_data:
            dist = (point[0]**2 + point[1]**2) ** 0.5
            if dist < min_distance:
                min_distance = dist
                obstacle_angle = math.atan2(point[1], point[0])
        
        if min_distance < 1.0:
            avoid_angle = obstacle_angle + math.pi / 2
            return (math.cos(avoid_angle), math.sin(avoid_angle))
        
        return desired_dir


class SensorFusion:
    """传感器融合模块"""
    
    def __init__(self):
        self.position = (0.0, 0.0)
        self.velocity = (0.0, 0.0)
        self.heading = 0.0
        logger.info("Sensor fusion initialized")
    
    def fuse_gps_imu(self, gps_data: Dict, imu_data: Tuple) -> Tuple[float, float, float]:
        if gps_data.get('fix', False):
            self.position = (gps_data.get('lat', 0), gps_data.get('lon', 0))
        
        ax, ay, az = imu_data[:3]
        gx, gy, gz = imu_data[3:]
        
        self.velocity = (gx, gy)
        self.heading += gz * 0.1
        
        return (*self.position, self.heading)
    
    def get_position(self) -> Tuple[float, float]:
        return self.position
    
    def get_heading(self) -> float:
        return self.heading


class AIManager:
    """AI管理器 - 整合所有AI模块"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        model_path = self.config.get('model_path', 'best.pt')
        if not os.path.exists(model_path):
            model_path = os.path.join(os.path.dirname(__file__), '..', model_path)
        
        llm_model = self.config.get('llm_model', 'deepseek')
        llm_backend = self.config.get('llm_backend', 'deepseek')
        
        self.weed_detector = WeedDetector(model_path)
        self.navigation = NavigationAI()
        self.sensor_fusion = SensorFusion()
        self.llm = LLMAssistant(model=llm_model, backend=llm_backend)
        
        self._running = False
        logger.info(f"AI Manager initialized (LLM: {llm_backend}/{llm_model})")
    
    def start(self):
        self._running = True
        logger.info("AI Manager started")
    
    def stop(self):
        self._running = False
        self.weed_detector.stop()
        logger.info("AI Manager stopped")
    
    def detect_weeds(self, frame) -> List[WeedDetection]:
        return self.weed_detector.detect_from_frame(frame)
    
    def process_camera_frame(self, frame_data: bytes) -> Dict:
        detections = self.weed_detector.detect_from_frame(frame_data)
        
        return {
            "detections": [
                {
                    "position": d.position,
                    "confidence": d.confidence,
                    "weed_type": d.weed_type,
                    "size": d.size
                }
                for d in detections
            ],
            "statistics": self.weed_detector.get_statistics()
        }
    
    def plan_navigation(self, current_pos: Tuple[float, float],
                        target_pos: Tuple[float, float],
                        obstacles: List = None) -> List[Tuple[float, float]]:
        if obstacles:
            for obs in obstacles:
                self.navigation.update_map([obs], current_pos)
        
        return self.navigation.plan_path(current_pos, target_pos)
    
    def fuse_sensors(self, gps_data: Dict, imu_data: Tuple) -> Tuple[float, float, float]:
        return self.sensor_fusion.fuse_gps_imu(gps_data, imu_data)
    
    def chat(self, message: str) -> str:
        return self.llm.chat(message)
    
    def analyze_detections(self, detections: List[WeedDetection]) -> str:
        if not detections:
            return "未检测到杂草目标"
        
        stats = self.weed_detector.get_statistics()
        summary = f"检测到 {len(detections)} 个杂草目标，平均置信度 {stats['avg_confidence']:.1%}"
        
        prompt = f"用户报告: {summary}。请给出处理建议。"
        return self.llm.chat(prompt)
    
    def diagnose_system(self, status: Dict) -> str:
        issues = []
        if status.get('battery', 100) < 20:
            issues.append("电池电量低")
        if not status.get('lidar_ok', True):
            issues.append("LiDAR传感器异常")
        if not status.get('camera_ok', True):
            issues.append("相机异常")
        
        if not issues:
            prompt = "系统状态正常。请给出简洁的确认回复。"
        else:
            issues_str = "、".join(issues)
            prompt = f"系统出现以下问题: {issues_str}。请给出诊断建议。"
        
        return self.llm.chat(prompt)
    
    def get_status(self) -> Dict:
        return {
            "weed_detector": {
                "available": self.weed_detector.yolo.available,
                "threshold": self.weed_detector.confidence_threshold,
                "statistics": self.weed_detector.get_statistics()
            },
            "navigation": {
                "grid_size": self.navigation.grid_size,
                "obstacles_mapped": len(self.navigation.occupancy_grid)
            },
            "sensor_fusion": {
                "position": self.sensor_fusion.get_position(),
                "heading": self.sensor_fusion.get_heading()
            },
            "llm": {
                "available": self.llm.available,
                "model": self.llm.model_name
            }
        }


class LLMAssistant:
    """本地大模型助手 - 支持Ollama/llama.cpp"""
    
    def __init__(self, model: str = "deepseek", backend: str = "deepseek"):
        self.model_name = model
        self.backend = backend
        self.client = None
        self.available = False
        self.connection_status = "未连接"
        self._init_client()
    
    def _init_client(self):
        if self.backend == "ollama":
            self._init_ollama()
        elif self.backend == "llama.cpp":
            self._init_llama_cpp()
        elif self.backend == "deepseek":
            self._init_deepseek()
        elif self.backend == "simulated":
            self._init_simulated()
        else:
            self._init_simulated()
    
    def _init_deepseek(self):
        try:
            from llama_cpp import Llama
            
            model_path = None
            search_paths = [
                os.path.expanduser("~/RayMind/models/"),
                os.path.expanduser("~/.cache/llama.cpp/models/"),
                "models/",
                ".",
            ]
            
            for search_dir in search_paths:
                if os.path.isdir(search_dir):
                    for f in os.listdir(search_dir):
                        if f.endswith('.gguf'):
                            model_path = os.path.join(search_dir, f)
                            break
                if model_path:
                    break
            
            if model_path is None:
                self.connection_status = "未找到GGUF模型"
                logger.warning("No GGUF model found")
                self._init_simulated()
                return
            
            self.client = DeepSeekClient(model_path)
            
            if self.client.is_available():
                self.available = True
                self.connection_status = f"已加载: {os.path.basename(model_path)}"
                logger.info(f"DeepSeek model loaded: {model_path}")
            else:
                self.connection_status = "模型加载失败"
                self._init_simulated()
                
        except ImportError:
            self.connection_status = "llama-cpp-python未安装"
            logger.warning("llama-cpp-python not installed")
            self._init_simulated()
        except Exception as e:
            self.connection_status = f"错误: {str(e)[:30]}"
            logger.error(f"DeepSeek init failed: {e}")
            self._init_simulated()
    
    def _init_ollama(self):
        try:
            import requests
            try:
                resp = requests.get("http://localhost:11434/api/tags", timeout=3)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get('models', [])
                    available_models = [m['name'] for m in models]
                    
                    ollama_version = data.get('version', 'unknown')
                    self.connection_status = f"已连接 (v{ollama_version})"
                    
                    target_model = self.model_name
                    if target_model not in available_models:
                        for m in available_models:
                            if m.startswith(self.model_name.split(':')[0]):
                                target_model = m
                                break
                    
                    self.client = OllamaClient(target_model)
                    self.available = True
                    logger.info(f"Ollama connected: {target_model}, available models: {available_models}")
                    return
            except requests.exceptions.ConnectionError:
                self.connection_status = "服务未运行 (请运行: ollama serve)"
            except requests.exceptions.Timeout:
                self.connection_status = "连接超时"
            except Exception as e:
                self.connection_status = f"连接错误: {str(e)[:30]}"
            
            logger.info("Ollama not available, using simulation mode")
            self._init_simulated()
            
        except ImportError:
            self.connection_status = "requests未安装"
            logger.warning("requests not installed, using simulation")
            self._init_simulated()
    
    def _init_llama_cpp(self):
        try:
            from llama_cpp import Llama
            model_path = os.path.expanduser("~/.cache/llama.cpp/models/{}/ggml-model.gguf".format(self.model_name))
            
            if os.path.exists(model_path):
                self.client = LlamaCppClient(model_path)
                self.available = True
                self.connection_status = "模型已加载"
                logger.info(f"llama.cpp loaded: {model_path}")
            else:
                logger.warning(f"Model not found: {model_path}, using simulation")
                self._init_simulated()
        except ImportError:
            self.connection_status = "llama-cpp-python未安装"
            logger.warning("llama-cpp-python not installed, using simulation")
            self._init_simulated()
        except Exception as e:
            self.connection_status = f"加载失败: {str(e)[:30]}"
            logger.warning(f"llama.cpp init failed: {e}, using simulation")
            self._init_simulated()
    
    def _init_simulated(self):
        self.client = SimulatedLLM()
        self.available = True
        self.connection_status = "模拟模式"
        logger.info("Using simulated LLM")
    
    def chat(self, message: str, system_prompt: str = None) -> str:
        if system_prompt is None:
            system_prompt = "你是RayMind智能农田机器人的AI助手。请用简洁的中文回复。"
        
        return self.client.generate(system_prompt, message)
    
    def chat_stream(self, message: str, callback, system_prompt: str = None):
        """流式对话"""
        if system_prompt is None:
            system_prompt = "你是RayMind智能农田机器人的AI助手。请用简洁的中文回复。"
        
        if hasattr(self.client, 'generate_stream'):
            for chunk in self.client.generate_stream(system_prompt, message):
                callback(chunk)
        else:
            result = self.chat(message, system_prompt)
            callback(result)
    
    def set_model(self, model: str):
        self.model_name = model
        self._init_client()
    
    def list_models(self) -> List[Dict]:
        if isinstance(self.client, OllamaClient):
            try:
                import requests
                resp = requests.get("http://localhost:11434/api/tags", timeout=3)
                if resp.status_code == 200:
                    models = resp.json().get('models', [])
                    return [
                        {
                            "name": m.get('name', ''),
                            "size": m.get('size', 0),
                            "modified": m.get('modified_at', '')
                        }
                        for m in models
                    ]
            except:
                pass
        return [{"name": self.model_name, "size": 0, "modified": ""}]
    
    def pull_model(self, model_name: str) -> bool:
        """下载模型"""
        try:
            import requests
            import threading
            
            def pull():
                try:
                    requests.post(
                        "http://localhost:11434/api/pull",
                        json={"name": model_name},
                        stream=True,
                        timeout=300
                    )
                except:
                    pass
            
            thread = threading.Thread(target=pull)
            thread.daemon = True
            thread.start()
            return True
        except:
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除模型"""
        try:
            import requests
            resp = requests.delete(
                "http://localhost:11434/api/delete",
                json={"name": model_name}
            )
            return resp.status_code == 200
        except:
            return False
    
    def get_ollama_status(self) -> Dict:
        """获取Ollama服务状态"""
        status = {
            "connected": self.available and self.backend == "ollama",
            "status": self.connection_status,
            "current_model": self.model_name,
            "backend": self.backend,
            "available_models": self.list_models()
        }
        
        if self.backend == "ollama":
            try:
                import requests
                resp = requests.get("http://localhost:11434/", timeout=2)
                status["server_version"] = resp.headers.get('Server', 'unknown')
            except:
                pass
        
        return status
    
    def restart_ollama(self) -> bool:
        """重启Ollama服务"""
        import subprocess
        try:
            subprocess.run(["pkill", "-f", "ollama"], timeout=5)
            time.sleep(1)
            subprocess.Popen(["ollama", "serve"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
            time.sleep(2)
            self._init_client()
            return True
        except:
            return False


class OllamaClient:
    """Ollama API客户端"""
    
    def __init__(self, model: str):
        self.model = model
        self.base_url = "http://localhost:11434"
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            import requests
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False
            }
            
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if resp.status_code == 200:
                return resp.json().get('message', {}).get('content', '')
            
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
        
        return "抱歉，当前无法连接到本地大模型服务。"
    
    def generate_stream(self, system_prompt: str, user_prompt: str):
        """流式生成"""
        try:
            import requests
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": True
            }
            
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=30
            )
            
            if resp.status_code == 200:
                for line in resp.iter_lines():
                    if line:
                        data = line.decode('utf-8')
                        if data.startswith('data: '):
                            content = data[6:]
                            if content == '[DONE]':
                                break
                            import json
                            try:
                                msg = json.loads(content)
                                if 'message' in msg and 'content' in msg['message']:
                                    yield msg['message']['content']
                            except:
                                pass
            
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            yield "抱歉，连接出错。"
    
    def get_embeddings(self, text: str) -> List[float]:
        """获取文本embedding"""
        try:
            import requests
            
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json=payload,
                timeout=10
            )
            
            if resp.status_code == 200:
                return resp.json().get('embedding', [])
            
        except Exception as e:
            logger.error(f"Ollama embeddings failed: {e}")
        
        return []
    
    def is_model_loaded(self) -> bool:
        """检查模型是否已加载"""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/ps", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('models', [])[0].get('name') == self.model if data.get('models') else False
        except:
            pass
        return False


class LlamaCppClient:
    """llama.cpp推理客户端"""
    
    def __init__(self, model_path: str):
        from llama_cpp import Llama
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=0
        )
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        try:
            full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
            
            output = self.llm(
                full_prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.9,
                stop=["User:", "System:"]
            )
            
            return output['choices'][0]['text'].strip()
            
        except Exception as e:
            logger.error(f"llama.cpp generation failed: {e}")
            return "抱歉，大模型推理失败。"
    
    def generate_stream(self, system_prompt: str, user_prompt: str):
        """流式生成"""
        try:
            full_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
            
            for output in self.llm(
                full_prompt,
                max_tokens=512,
                temperature=0.7,
                top_p=0.9,
                stream=True,
                stop=["User:", "System:"]
            ):
                if 'choices' in output and output['choices']:
                    text = output['choices'][0].get('text', '')
                    if text:
                        yield text
            
        except Exception as e:
            logger.error(f"llama.cpp stream failed: {e}")
            yield "抱歉，大模型推理失败。"


class DeepSeekClient:
    """DeepSeek本地模型客户端 - 直接加载GGUF模型"""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.llm = None
        self._load_model()
    
    def _load_model(self):
        if self.model_path is None:
            self._find_model()
        
        if self.model_path and os.path.exists(self.model_path):
            try:
                from llama_cpp import Llama
                
                logger.info(f"Loading DeepSeek model from: {self.model_path}")
                
                self.llm = Llama(
                    model_path=self.model_path,
                    n_ctx=512,
                    n_threads=2,
                    n_gpu_layers=0,
                    use_mmap=True,
                    use_mlock=False,
                    verbose=False,
                    low_vram=True
                )
                
                logger.info("DeepSeek model loaded successfully")
                
            except ImportError:
                logger.error("llama-cpp-python not installed")
                logger.info("安装: pip install llama-cpp-python")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
        else:
            logger.warning(f"Model not found: {self.model_path}")
            logger.info("请下载DeepSeek GGUF模型文件")
    
    def _find_model(self):
        search_paths = [
            os.path.expanduser("~/RayMind/models/deepseek-coder-q4_k_m.gguf"),
            os.path.expanduser("~/RayMind/models/deepseek-llm-7b-chat-q4_0.gguf"),
            os.path.expanduser("~/.cache/llama.cpp/models/deepseek-coder-q4_k_m.gguf"),
            os.path.expanduser("~/.cache/llama.cpp/models/deepseek-llm-7b-chat-q4_0.gguf"),
            "/opt/raymind/models/deepseek-coder-q4_k_m.gguf",
            "models/deepseek-coder-q4_k_m.gguf",
            "deepseek-coder-q4_k_m.gguf",
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                self.model_path = path
                logger.info(f"Found model at: {path}")
                return
        
        default_dir = os.path.expanduser("~/RayMind/models")
        if os.path.exists(default_dir):
            for f in os.listdir(default_dir):
                if f.endswith('.gguf'):
                    self.model_path = os.path.join(default_dir, f)
                    logger.info(f"Found model: {self.model_path}")
                    return
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.llm is None:
            return "模型未加载，请确保已安装llama-cpp-python并下载GGUF模型文件。"
        
        try:
            model_file = os.path.basename(self.model_path).lower()
            
            if "deepseek-r1" in model_file or "r1" in model_file:
                prompt = f"USER: {system_prompt}\n\n{user_prompt}\n\nASSISTANT:"
            elif "coder" in model_file:
                prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{user_prompt}<|end|>\n<|assistant|>\n"
            else:
                prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
            
            output = self.llm(
                prompt,
                max_tokens=1024,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stream=False
            )
            
            result = output['choices'][0]['text'].strip()
            
            if "r1" in model_file and "reasoning" in result.lower():
                parts = result.split("</think>")
                if len(parts) > 1:
                    result = parts[-1].strip()
            
            return result
            
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            return f"推理失败: {str(e)}"
    
    def generate_stream(self, system_prompt: str, user_prompt: str):
        """流式生成"""
        if self.llm is None:
            yield "模型未加载"
            return
        
        try:
            model_file = os.path.basename(self.model_path).lower()
            
            if "deepseek-r1" in model_file or "r1" in model_file:
                prompt = f"USER: {system_prompt}\n\n{user_prompt}\n\nASSISTANT:"
            elif "coder" in model_file:
                prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{user_prompt}<|end|>\n<|assistant|>\n"
            else:
                prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
            
            for output in self.llm(
                prompt,
                max_tokens=1024,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                repeat_penalty=1.1,
                stream=True
            ):
                if 'choices' in output and output['choices']:
                    text = output['choices'][0].get('text', '')
                    if text:
                        yield text
            
        except Exception as e:
            logger.error(f"DeepSeek stream failed: {e}")
            yield f"推理失败: {str(e)}"
    
    def is_available(self) -> bool:
        return self.llm is not None
    
    @staticmethod
    def download_model(model_name: str = "deepseek-coder-1.3b-Q4_K_M.gguf") -> str:
        """下载DeepSeek GGUF模型"""
        import urllib.request
        import zipfile
        
        model_dir = os.path.expanduser("~/RayMind/models")
        os.makedirs(model_dir, exist_ok=True)
        
        model_urls = {
            "deepseek-coder-1.3b-Q4_K_M": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/deepseek-coder-1.3b-q4_k_m.gguf",
            ],
            "deepseek-coder-6.7b-Q4_K_M": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/deepseek-coder-6.7b-q4_k_m.gguf",
            ],
            "deepseek-llm-7b-chat-q4_0": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/deepseek-llm-7b-chat-q4_0.gguf",
            ],
            "deepseek-llm-8b-chat-q4_0": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF/resolve/main/deepseek-llm-8b-chat-q4_0.gguf",
            ],
            "deepseek-r1-q4": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
            ],
            "deepseek-r1-1.5b-q4": [
                "https://modelscope.cn/models/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF/resolve/main/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf",
            ],
        }
        
        download_commands = {
            "deepseek-r1-1.5b-q4": "modelscope download --model unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF --local_dir ~/RayMind/models",
            "deepseek-r1-q4": "modelscope download --model unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF --local_dir ~/RayMind/models",
            "deepseek-coder-1.3b-q4_k_m": "modelscope download --model unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF --local_dir ~/RayMind/models",
        }
        
        urls = model_urls.get(model_name, model_urls["deepseek-coder-1.3b-Q4_K_M"])
        dest_path = os.path.join(model_dir, model_name)
        
        if os.path.exists(dest_path):
            logger.info(f"Model already exists: {dest_path}")
            return dest_path
        
        for url in urls:
            logger.info(f"Trying: {url}")
            try:
                urllib.request.urlretrieve(url, dest_path)
                logger.info(f"Downloaded to: {dest_path}")
                return dest_path
            except Exception as e:
                logger.warning(f"Failed: {e}")
                continue
        
        logger.error("All download sources failed")
        return None


class SimulatedLLM:
    """模拟大模型 - 用于测试"""
    
    def __init__(self):
        self.responses = {
            "hello": "你好！我是RayMind AI助手。",
            "status": "系统运行正常，各传感器状态良好。",
            "help": "我可以帮助你：1.分析杂草检测结果 2.诊断系统问题 3.提供操作建议",
            "default": "收到你的消息。当前系统状态正常，准备就绪。"
        }
    
    def _analyze_intent(self, message: str) -> str:
        msg = message.lower()
        
        if any(w in msg for w in ["你好", "hello", "hi", "在吗"]):
            return "hello"
        elif any(w in msg for w in ["状态", "怎么样", "正常"]):
            return "status"
        elif any(w in msg for w in ["帮助", "help", "能做什么", "功能"]):
            return "help"
        
        detection_keywords = ["检测", "杂草", "目标", "识别"]
        if any(w in msg for w in detection_keywords):
            return "detection"
        
        diag_keywords = ["问题", "错误", "故障", "异常", "诊断"]
        if any(w in msg for w in diag_keywords):
            return "diagnosis"
        
        nav_keywords = ["导航", "路径", "规划", "去哪里"]
        if any(w in msg for w in nav_keywords):
            return "navigation"
        
        return "default"
    
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        intent = self._analyze_intent(user_prompt)
        
        responses = {
            "hello": "你好！我是RayMind智能农田机器人AI助手。你可以让我分析检测结果、诊断系统问题或提供操作建议。",
            "status": "当前系统状态：\n- 机器人：待机状态\n- 电池：100%\n- 传感器：正常\n- 定位：已就绪",
            "help": "我可以帮助你：\n1. 分析杂草检测结果\n2. 诊断系统问题\n3. 提供导航建议\n4. 解释操作流程\n\n直接告诉我你需要什么帮助即可。",
            "detection": "根据当前检测结果，建议执行以下操作：\n1. 确认检测到的杂草位置\n2. 评估清除优先级\n3. 启动激光清除程序\n\n需要我帮你分析具体的检测数据吗？",
            "diagnosis": "系统诊断结果：\n- 所有传感器正常\n- 通信链路稳定\n- 电池电量充足\n- 执行机构就绪\n\n未发现异常情况。",
            "navigation": "导航建议：\n1. 确认目标位置\n2. 启用自主导航模式\n3. 保持障碍物检测开启\n\n需要我帮你规划具体路径吗？",
            "default": "明白了。请告诉我具体需要什么帮助——分析检测结果、诊断问题、或者导航建议？"
        }
        
        return responses.get(intent, responses["default"])
    
    def generate_stream(self, system_prompt: str, user_prompt: str):
        """流式生成（模拟）"""
        response = self.generate(system_prompt, user_prompt)
        for char in response:
            yield char
            time.sleep(0.02)
