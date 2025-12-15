"""Text-to-Speech module for robot audio feedback."""

import threading
import queue
from config import TTS_ENABLED, TTS_DEVICE

class TTSEngine:
    def __init__(self):
        self.enabled = TTS_ENABLED
        self.device = TTS_DEVICE
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        self.engine = None
        
        if self.enabled:
            try:
                import pyttsx3
                self.engine = pyttsx3.init()
                # Try to set properties
                try:
                    self.engine.setProperty('rate', 150)  # Speed
                    self.engine.setProperty('volume', 1.0)  # Volume
                except:
                    pass  # Ignore property errors
                
                self.worker_thread = threading.Thread(target=self._worker, daemon=True)
                self.worker_thread.start()
            except Exception as e:
                print(f"[TTS] Init failed: {e}")
                self.enabled = False
    
    def _worker(self):
        """Background worker that processes speech queue."""
        while True:
            try:
                text = self.speech_queue.get(timeout=1)
                if text is None:
                    break
                self._speak_blocking(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS] Error: {e}")
    
    def _speak_blocking(self, text):
        """Use pyttsx3 to generate speech."""
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS] Speak failed: {e}")
    
    def speak(self, text):
        """Queue text for asynchronous speech."""
        if self.enabled and text:
            self.speech_queue.put(text)
    
    def shutdown(self):
        """Shutdown TTS engine."""
        if self.worker_thread:
            self.speech_queue.put(None)
            self.worker_thread.join(timeout=2)


# Global TTS instance
_tts = None

def init():
    """Initialize TTS engine."""
    global _tts
    if _tts is None:
        _tts = TTSEngine()

def speak(text):
    """Speak text via TTS."""
    if _tts:
        _tts.speak(text)

def shutdown():
    """Shutdown TTS."""
    if _tts:
        _tts.shutdown()
