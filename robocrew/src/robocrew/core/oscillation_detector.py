from collections import deque
import logging

logger = logging.getLogger(__name__)

class OscillationDetector:
    """
    Detects repeating patterns in action history to prevent infinite loops.
    """
    def __init__(self, history_len=20):
        self.action_history = deque(maxlen=history_len)
        self.oscillation_threshold = 3  # How many times a pattern must repeat
        
    def record_action(self, action_name: str, args: dict = None):
        """Record an action and checks for oscillation."""
        # Simplify args for comparison (ignore small float differences if needed, but for now exact header is fine)
        # We construct a signature like "turn_left" or "turn_left|90"
        
        sig = action_name
        # If it's a move/turn, maybe include direction/sign? 
        # For simplicity, let's just use the tool name. 
        # "move_forward", "move_backward" are distinct.
        
        self.action_history.append(sig)
        
    def detect_oscillation(self) -> bool:
        """
        Check if the recent history contains a repeating pattern.
        Returns True if oscillation is detected.
        """
        history = list(self.action_history)
        n = len(history)
        
        if n < 4:
            return False
            
        # Check for 2-step loop (A, B, A, B, A, B)
        # We need at least 4 items for A, B, A, B
        if n >= 4:
            # Check last 4: [..., A, B, A, B]
            if history[-1] == history[-3] and history[-2] == history[-4]:
                # Require one more repetition for confirmation? 
                # A, B, A, B is strong evidence.
                # Let's say we need 3 cycles for small loops to be sure it's not just maneuvering.
                # A, B, A, B, A, B (6 items)
                if n >= 6:
                     if (history[-1] == history[-3] == history[-5]) and \
                        (history[-2] == history[-4] == history[-6]):
                        logger.warning(f"Oscillation Detected (2-step): {history[-6:]}")
                        return True
                        
        # Check for 1-step loop (A, A, A, A) - e.g. bumping into wall repeatedly
        if n >= 4:
             if history[-1] == history[-2] == history[-3] == history[-4]:
                 logger.warning(f"Oscillation Detected (1-step): {history[-4:]}")
                 return True
                 
        return False
        
    def get_warning_message(self) -> str:
        return "SYSTEM WARNING: You are repeating the same actions over and over. STOP. Do not try the same thing again. Try a completely different strategy (e.g. turn around, go back, or ask for help)."
