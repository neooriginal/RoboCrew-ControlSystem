"""
VLA System Coordinator
Central entry point for VLA functionality.
"""

from .recorder import VLARecorder
from .trainer import VLATrainer
from .executor import VLAExecutor
import threading

class VLASystem:
    def __init__(self):
        self.recorder = VLARecorder()
        self.trainer = VLATrainer()
        self.executor = VLAExecutor()
        self.training_thread = None
        
    def start_recording(self, dataset_name=None):
        return self.recorder.start_recording(dataset_name)
        
    def stop_recording(self):
        return self.recorder.stop_recording()

    def train_model(self, dataset_name, model_name, epochs=10):
        if self.trainer.training:
             return False, "Already training"
        
        # Resolve dataset path
        dataset_path = self.recorder.dataset_root / dataset_name
        if not dataset_path.exists():
            return False, f"Dataset {dataset_name} not found"
            
        # Start in thread
        self.training_thread = threading.Thread(
            target=self.trainer.train,
            args=(dataset_path, model_name, int(epochs)),
            daemon=True
        )
        self.training_thread.start()
        return True, "Training started"

    def stop_training(self):
        self.trainer.stop_training()
        return True
        
    def get_status(self):
        return {
            "recorder": self.recorder.get_status(),
            "training": self.trainer.training,
            "execution": self.executor.running
        }

    def start_execution(self, model_name):
        return self.executor.start_execution(model_name)
        
    def stop_execution(self):
        return self.executor.stop_execution()
