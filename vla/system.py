"""
VLA System Coordinator
Central entry point for VLA functionality.
Configures absolute paths for persistence.
"""

from pathlib import Path
from .recorder import VLARecorder
from .executor import VLAExecutor

class VLASystem:
    def __init__(self):
        # Calculate Absolute Paths
        # system.py is in /vla/
        # Root is / (parent of vla)
        self.root_dir = Path(__file__).parent.parent.resolve()
        
        self.datasets_dir = self.root_dir / "datasets"
        self.models_dir = self.root_dir / "models"
        
        # Ensure directories exist
        self.datasets_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        
        # Initialize sub-systems with absolute paths
        self.recorder = VLARecorder(dataset_dir=str(self.datasets_dir))
        self.executor = VLAExecutor(models_dir=str(self.models_dir))
        
    def start_recording(self, dataset_name=None):
        return self.recorder.start_recording(dataset_name)
        
    def stop_recording(self):
        return self.recorder.stop_recording()

    def delete_last_episode(self):
        return self.recorder.delete_last_episode()
        
    def get_status(self):
        return {
            "recorder": self.recorder.get_status(),
            "execution": self.executor.running
        }

    def start_execution(self, model_name):
        return self.executor.start_execution(model_name)
        
    def stop_execution(self):
        return self.executor.stop_execution()
