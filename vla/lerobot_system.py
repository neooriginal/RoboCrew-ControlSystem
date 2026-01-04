"""
LeRobot VLA System - Unified interface for recording, training, and execution.
"""

import logging
from pathlib import Path
from typing import Optional

from vla.lerobot_recorder import LeRobotRecorder, LEROBOT_AVAILABLE
from vla.lerobot_trainer import LeRobotTrainer
from vla.lerobot_executor import LeRobotExecutor

logger = logging.getLogger(__name__)


class LeRobotVLASystem:
    """
    Unified VLA system using LeRobot for everything.
    
    Provides:
    - Dataset recording in LeRobot format
    - ACT policy training via web UI
    - Policy execution via RobotClient
    """
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        
        # Initialize components
        self.recorder = LeRobotRecorder(str(self.base_dir / "datasets"))
        self.trainer = LeRobotTrainer(
            str(self.base_dir / "datasets"),
            str(self.base_dir / "models")
        )
        self.executor = LeRobotExecutor(str(self.base_dir / "models"))
        
        logger.info(f"LeRobot VLA System initialized. LeRobot available: {LEROBOT_AVAILABLE}")
        
    # ─── Recording ───
    
    def list_datasets(self):
        """List all datasets."""
        return self.recorder.list_datasets()
        
    def create_dataset(self, name: str):
        """Create new dataset for recording."""
        return self.recorder.create_dataset(name)
        
    def load_dataset(self, name: str):
        """Load existing dataset."""
        return self.recorder.load_dataset(name)
        
    def start_recording(self, dataset_name: str = None):
        """Start recording an episode. Creates or loads dataset if name provided."""
        if dataset_name:
            # Try to load existing dataset, create if doesn't exist
            success, msg = self.recorder.load_dataset(dataset_name)
            if not success:
                success, msg = self.recorder.create_dataset(dataset_name)
                if not success:
                    return False, msg
        return self.recorder.start_recording()
        
    def stop_recording(self):
        """Stop recording and save episode."""
        return self.recorder.stop_recording()
        
    def finalize_dataset(self):
        """Finalize dataset for training."""
        return self.recorder.finalize_dataset()
        
    def get_recording_status(self):
        """Get recording status."""
        return self.recorder.get_status()
        
    # ─── Training ───
    
    def list_trainable_datasets(self):
        """List datasets ready for training."""
        datasets = self.recorder.list_datasets()
        return [d for d in datasets if d.get("is_lerobot", False)]
        
    def start_training(self, dataset_name: str, model_name: str, epochs: int = 100):
        """Start training an ACT policy."""
        return self.trainer.start_training(
            dataset_name=dataset_name,
            output_name=model_name,
            num_epochs=epochs,
            batch_size=8,
            policy_type="act"
        )
        
    def stop_training(self):
        """Stop ongoing training."""
        return self.trainer.stop_training()
        
    def get_training_status(self):
        """Get training status."""
        return self.trainer.get_status()
        
    # ─── Execution ───
    
    def list_models(self):
        """List trained models."""
        return self.executor.list_models()
        
    def load_model(self, model_name: str):
        """Load a trained model."""
        return self.executor.load_model(model_name)
        
    def start_execution(self, task: str = ""):
        """Start policy execution."""
        return self.executor.start_execution(task)
        
    def stop_execution(self):
        """Stop execution."""
        return self.executor.stop_execution()
        
    def get_execution_status(self):
        """Get execution status."""
        return self.executor.get_status()
        
    # ─── Combined Status ───
    
    def get_status(self):
        """Get complete system status."""
        return {
            "lerobot_available": LEROBOT_AVAILABLE,
            "recording": self.recorder.get_status(),
            "training": self.trainer.get_status(),
            "execution": self.executor.get_status()
        }


# Global instance
_vla_system: Optional[LeRobotVLASystem] = None


def get_vla_system() -> LeRobotVLASystem:
    """Get or create the global VLA system instance."""
    global _vla_system
    if _vla_system is None:
        _vla_system = LeRobotVLASystem()
    return _vla_system
