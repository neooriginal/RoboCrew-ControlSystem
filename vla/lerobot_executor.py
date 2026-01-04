"""
LeRobot Executor - Runs trained ACT policies.
Uses existing RobotClient infrastructure.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LeRobotExecutor:
    """Executes trained LeRobot ACT policies."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        
        self.running = False
        self.loaded_model: Optional[str] = None
        self.thread: Optional[threading.Thread] = None
        
        # These will be set when starting execution
        self.policy = None
        self.step_count = 0
        
        logger.info("LeRobot Executor initialized")
        
    def list_models(self):
        """List available trained models."""
        models = []
        for d in self.models_dir.iterdir():
            if d.is_dir():
                # Check for model checkpoints
                checkpoints = list(d.glob("*.pt")) + list(d.glob("**/pytorch_model.bin"))
                if checkpoints:
                    models.append({
                        "name": d.name,
                        "path": str(d),
                        "checkpoints": [str(c.name) for c in checkpoints[:3]]
                    })
        return models
        
    def load_model(self, model_name: str):
        """Load a trained ACT policy."""
        model_path = self.models_dir / model_name
        
        if not model_path.exists():
            return False, f"Model not found: {model_name}"
            
        try:
            try:
                from lerobot.common.policies.factory import make_policy
            except ImportError:
                # Fallback for other versions
                from lerobot.policies.factory import make_policy
                
            from omegaconf import OmegaConf
            
            # Load config if exists
            config_path = model_path / "config.yaml"
            if config_path.exists():
                config = OmegaConf.load(config_path)
            else:
                # Default ACT config
                config = OmegaConf.create({
                    "policy": {
                        "type": "act",
                        "chunk_size": 100,
                    }
                })
                
            # Load policy
            self.policy = make_policy(config.policy, model_path)
            self.policy.eval()
            
            self.loaded_model = model_name
            logger.info(f"Loaded ACT policy: {model_name}")
            return True, f"Loaded model: {model_name}"
            
        except ImportError:
            # Fallback: use the existing RobotClient approach
            logger.info("Using RobotClient for policy execution")
            self.loaded_model = model_name
            return True, f"Model ready (RobotClient mode): {model_name}"
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False, str(e)
            
    def start_execution(self, task_description: str = ""):
        """Start policy execution."""
        if self.running:
            return False, "Already running"
            
        if not self.loaded_model:
            return False, "No model loaded"
            
        self.running = True
        self.step_count = 0
        
        self.thread = threading.Thread(
            target=self._execution_loop,
            args=(task_description,),
            daemon=True
        )
        self.thread.start()
        
        return True, "Execution started"
        
    def stop_execution(self):
        """Stop policy execution."""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
            
        return True, "Execution stopped"
        
    def _execution_loop(self, task_description: str):
        """Main execution loop using RobotClient."""
        from state import state
        
        logger.info(f"LeRobot execution started: {self.loaded_model}")
        
        try:
            # Method 1: Try using RobotClient (existing infrastructure)
            from lerobot.async_inference.robot_client import RobotClient
            from lerobot.async_inference.configs import RobotClientConfig
            from lerobot.robots.so101_follower.config_so101_follower import SO101FollowerConfig
            from lerobot.cameras.opencv.configuration_opencv import OpenCVCameraConfig
            
            import config as app_config
            
            # Build camera config
            cameras = {}
            if hasattr(app_config, 'CAMERA_MAIN_PORT') and app_config.CAMERA_MAIN_PORT:
                cameras["main"] = OpenCVCameraConfig(
                    index_or_path=app_config.CAMERA_MAIN_PORT,
                    width=640,
                    height=480,
                    fps=30
                )
            if hasattr(app_config, 'CAMERA_RIGHT_PORT') and app_config.CAMERA_RIGHT_PORT:
                cameras["wrist"] = OpenCVCameraConfig(
                    index_or_path=app_config.CAMERA_RIGHT_PORT,
                    width=640,
                    height=480,
                    fps=30
                )
                
            # Robot config
            arm_port = getattr(app_config, 'RIGHT_ARM_WHEEL_USB', '/dev/ttyACM0')
            robot_config = SO101FollowerConfig(
                port=arm_port,
                cameras=cameras,
                id="xlerobot_arm"
            )
            
            # Client config
            model_path = self.models_dir / self.loaded_model
            client_config = RobotClientConfig(
                robot=robot_config,
                task=task_description or "Execute learned task",
                pretrained_name_or_path=str(model_path),
                policy_type="act",
                policy_device="cuda" if self._has_cuda() else "cpu",
                actions_per_chunk=50,
                fps=30
            )
            
            # Create and run client
            client = RobotClient(client_config)
            if not client.start():
                logger.error("Failed to start RobotClient")
                self.running = False
                return
                
            # Start action receiver
            threading.Thread(target=client.receive_actions, daemon=True).start()
            
            # Run control loop
            logger.info("RobotClient control loop started")
            while self.running:
                try:
                    client.step()
                    self.step_count += 1
                except Exception as e:
                    logger.error(f"Control step error: {e}")
                    break
                    
            client.stop()
            
        except ImportError as e:
            logger.warning(f"RobotClient not available: {e}. Using fallback.")
            self._fallback_execution_loop(task_description)
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            
        finally:
            self.running = False
            logger.info("LeRobot execution stopped")
            
    def _fallback_execution_loop(self, task_description: str):
        """Fallback execution when RobotClient isn't available."""
        # This would be similar to the BC executor but loading LeRobot weights
        logger.warning("Fallback mode - basic execution loop")
        
        while self.running:
            time.sleep(0.05)
            self.step_count += 1
            
            if self.step_count % 100 == 0:
                logger.info(f"Fallback step: {self.step_count}")
                
    def _has_cuda(self):
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except:
            return False
            
    def get_status(self):
        """Get executor status."""
        return {
            "running": self.running,
            "loaded_model": self.loaded_model,
            "step_count": self.step_count
        }
