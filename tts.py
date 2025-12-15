"""Text-to-Speech module for robot audio feedback using gTTS."""

import threading
import queue
import tempfile
import os
from gtts import gTTS
from config import TTS_ENABLED, TTS_DEVICE

# Try to import pygame for audio playback
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[TTS] Warning: pygame not available, TTS will be disabled")

class TTSEngine:
    def __init__(self):
        self.enabled = TTS_ENABLED and PYGAME_AVAILABLE
        self.device = TTS_DEVICE
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        
        if self.enabled:
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            print("[TTS] Initialized (using gTTS with Google voices)")
        else:
            print("[TTS] Disabled (pygame or gTTS not available)")
    
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
        """Generate speech using gTTS and play it."""
        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file = fp.name
            
            # Generate speech with gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(temp_file)
            
            # Play the audio file
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
        except Exception as e:
            print(f"[TTS] Speech error: {e}")
    
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
