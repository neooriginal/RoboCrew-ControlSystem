from collections import deque
import logging

logger = logging.getLogger(__name__)

class OscillationDetector:
    def __init__(self, history_len=20):
        self.action_history = deque(maxlen=history_len)
        self.oscillation_threshold = 3
        
    def record_action(self, action_name: str, args: dict = None):
        self.action_history.append(action_name)
        
    def detect_oscillation(self) -> bool:
        history = list(self.action_history)
        n = len(history)
        
        if n < 4:
            return False
            
        if n >= 6:
             if (history[-1] == history[-3] == history[-5]) and \
                (history[-2] == history[-4] == history[-6]):
                logger.warning(f"Oscillation Detected (2-step): {history[-6:]}")
                return True

        if n >= 4:
             if history[-1] == history[-2] == history[-3] == history[-4]:
                 logger.warning(f"Oscillation Detected (1-step): {history[-4:]}")
                 return True
                 
        return False
        
    def get_warning_message(self) -> str:
        return "SYSTEM WARNING: You are repeating the same actions. STOP and try a different strategy."
