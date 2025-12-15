"""Text-to-Speech module for robot audio feedback."""

import threading
import queue
import subprocess
import os
from config import TTS_ENABLED, TTS_DEVICE

class TTSEngine:
    def __init__(self):
        self.enabled = TTS_ENABLED
        self.device = TTS_DEVICE
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        
        if self.enabled:
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
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
        """Use espeak to generate speech with specified ALSA device."""
        try:
            # Use espeak with ALSA device
            env = os.environ.copy()
            env['AUDIODEV'] = self.device
            
            subprocess.run(
                ['espeak', text],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
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
