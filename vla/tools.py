"""
VLA Tools for AI Agent.
This file defines the interface that the AI Agent can use to invoke VLA capabilities.
"""

from typing import Optional
from state import state

class VLATools:
    @staticmethod
    def run_vla_action(model_name: str, duration_seconds: float = 5.0) -> str:
        """
        Executes a specific VLA model/skill (e.g. 'pickup_cup', 'wave_hello') for a duration.
        
        Args:
            model_name (str): The name of the trained model to execute.
            duration_seconds (float): Max duration to run if the model doesn't self-terminate.
            
        Returns:
            str: Result status message.
        """
        vla = state.get_vla_system()
        if not vla:
            return "Error: VLA System unavailable"
            
        success, msg = vla.start_execution(model_name)
        if not success:
            return f"Error starting model '{model_name}': {msg}"
            
        return f"Started executing '{model_name}'. Will run indefinitely until stopped. (Duration control not yet implemented)"

    @staticmethod
    def stop_vla_action() -> str:
        """Stops any currently running VLA model."""
        vla = state.get_vla_system()
        if not vla:
            return "Error: VLA System unavailable"
            
        vla.stop_execution()
        return "VLA execution stopped."

    @staticmethod
    def list_vla_skills() -> list[str]:
        """Lists available VLA models/skills."""
        vla = state.get_vla_system()
        if not vla:
            return []
            
        root = vla.executor.models_dir
        if not root.exists():
            return []
            
        return [f.stem for f in root.glob("*.pth")]
