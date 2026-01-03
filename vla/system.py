"""
VLA System Coordinator
Central entry point for VLA functionality.
"""

from .recorder import VLARecorder
from .executor import VLAExecutor
import threading

class VLASystem:
    def __init__(self):
        self.recorder = VLARecorder()
        self.executor = VLAExecutor()
        
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

    def start_execution(self, model_name):
        return self.executor.start_execution(model_name)
        
    def stop_execution(self):
        return self.executor.stop_execution()
