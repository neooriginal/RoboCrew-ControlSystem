"""
LeRobot Training Manager.
Handles training ACT policies via web UI.
"""

import logging
import threading
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LeRobotTrainer:
    """Manages LeRobot ACT policy training."""
    
    def __init__(self, datasets_dir: str = "datasets", models_dir: str = "models"):
        self.datasets_dir = Path(datasets_dir)
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.training = False
        self.process: Optional[subprocess.Popen] = None
        self.progress = 0
        self.status_message = "Idle"
        self.log_lines = []
        
    def start_training(
        self,
        dataset_name: str,
        output_name: str,
        num_epochs: int = 100,
        batch_size: int = 8,
        policy_type: str = "act"
    ):
        """Start training an ACT policy on a dataset."""
        
        if self.training:
            return False, "Training already in progress"
            
        dataset_path = self.datasets_dir / dataset_name
        if not dataset_path.exists():
            return False, f"Dataset not found: {dataset_name}"
            
        output_path = self.models_dir / output_name
        
        self.training = True
        self.progress = 0
        self.status_message = "Starting training..."
        self.log_lines = []
        
        # Run training in background thread
        thread = threading.Thread(
            target=self._training_thread,
            args=(str(dataset_path), str(output_path), num_epochs, batch_size, policy_type),
            daemon=True
        )
        thread.start()
        
        return True, "Training started"
        
    def _training_thread(self, dataset_path: str, output_path: str, num_epochs: int, batch_size: int, policy_type: str):
        """Background training thread."""
        
        try:
            # Extract paths
            dataset_dir = str(Path(dataset_path).parent)  # e.g., "datasets"
            dataset_name = Path(dataset_path).name  # e.g., "Ttest"
            model_name = Path(output_path).name
            
            # Build lerobot training command
            # Use --dataset.root for local path and just dataset name for repo_id
            cmd = [
                "lerobot-train",
                f"--dataset.repo_id={dataset_name}",
                f"--dataset.root={dataset_dir}",
                f"--policy.type={policy_type}",
                f"--policy.repo_id={model_name}",
            ]
            
            logger.info(f"Starting training: {' '.join(cmd)}")
            self.status_message = "Training in progress..."
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output
            for line in self.process.stdout:
                line = line.strip()
                if line:
                    self.log_lines.append(line)
                    # Keep last 100 lines
                    if len(self.log_lines) > 100:
                        self.log_lines.pop(0)
                        
                    # Parse progress from output
                    if "epoch" in line.lower() and "/" in line:
                        try:
                            # Try to parse "Epoch X/Y" format
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if "/" in part and part.replace("/", "").replace("-", "").isdigit():
                                    current, total = part.split("/")
                                    self.progress = int(int(current) / int(total) * 100)
                                    break
                        except:
                            pass
                            
            # Wait for process to finish
            self.process.wait()
            
            if self.process.returncode == 0:
                self.status_message = "Training complete!"
                self.progress = 100
                logger.info(f"Training complete: {output_path}")
            else:
                # Log last few lines for debugging
                last_lines = '\n'.join(self.log_lines[-10:])
                self.status_message = f"Training failed (code {self.process.returncode})"
                logger.error(f"Training failed with code {self.process.returncode}. Last output:\n{last_lines}")
                
        except Exception as e:
            self.status_message = f"Error: {e}"
            logger.error(f"Training error: {e}")
            
        finally:
            self.training = False
            self.process = None
            
    def stop_training(self):
        """Stop ongoing training."""
        if not self.training or not self.process:
            return False, "No training in progress"
            
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except:
            self.process.kill()
            
        self.training = False
        self.status_message = "Training cancelled"
        return True, "Training stopped"
        
    def get_status(self):
        """Get current training status."""
        return {
            "training": self.training,
            "progress": self.progress,
            "status": self.status_message,
            "logs": self.log_lines[-20:]  # Last 20 lines
        }
        
    def list_models(self):
        """List trained models."""
        models = []
        for d in self.models_dir.iterdir():
            if d.is_dir():
                # Check for checkpoint files
                has_checkpoint = any(d.glob("*.pt")) or any(d.glob("checkpoints/*"))
                models.append({
                    "name": d.name,
                    "path": str(d),
                    "ready": has_checkpoint
                })
        return models
