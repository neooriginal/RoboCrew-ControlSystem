"""Text-to-Speech module for robot audio feedback using gTTS."""

import threading
import queue
import tempfile
import os
import subprocess
from gtts import gTTS
from config import TTS_ENABLED, TTS_DEVICE


class TTSEngine:
    def __init__(self):
        self.enabled = TTS_ENABLED
        self.device = TTS_DEVICE
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        
        if self.enabled:
            # Check if we have an audio player available
            self.audio_player = self._find_audio_player()
            if self.audio_player:
                self.worker_thread = threading.Thread(target=self._worker, daemon=True)
                self.worker_thread.start()
                print(f"[TTS] Initialized with Google voices (using {self.audio_player})")
            else:
                print("[TTS] No audio player found. Install mpg123, ffplay, or mpg321")
                self.enabled = False
        else:
            print("[TTS] TTS disabled in config")
    
    def _find_audio_player(self):
        """Find an available audio player on the system."""
        # aplay is more reliable on headless Linux systems
        players = ['aplay', 'mpg123', 'ffplay', 'mpg321', 'play']
        
        for player in players:
            try:
                subprocess.run([player, '--version'], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=1)
                return player
            except:
                continue
        return None
    
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
                print(f"[TTS] Worker error: {e}")
    
    def _speak_blocking(self, text):
        """Generate speech using gTTS and play it."""
        import sys
        temp_mp3 = None
        temp_wav = None
        try:
            print(f"[TTS] Generating: '{text}'")
            sys.stdout.flush()
            
            # Create temporary file for MP3
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_mp3 = fp.name
            
            # Generate speech with gTTS (this requires internet)
            print(f"[TTS] Connecting to Google TTS API...")
            sys.stdout.flush()
            
            tts = gTTS(text=text, lang='en', slow=False, timeout=5)
            tts.save(temp_mp3)
            
            print(f"[TTS] MP3 created: {temp_mp3}")
            sys.stdout.flush()
            
            # Convert MP3 to WAV using mpg123
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as fp:
                temp_wav = fp.name
            
            print(f"[TTS] Converting to WAV...")
            sys.stdout.flush()
            
            # Decode MP3 to WAV
            result = subprocess.run(['mpg123', '-w', temp_wav, temp_mp3], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE,
                         timeout=5,
                         check=False)
            
            if result.returncode != 0:
                print(f"[TTS] MP3 decode failed: {result.stderr.decode()}")
                sys.stdout.flush()
                return
            
            print(f"[TTS] WAV created, playing...")
            sys.stdout.flush()
            
            # Play WAV with aplay on HDMI
            cmd = ['aplay', '-D', 'plughw:1,0', temp_wav]
            
            result = subprocess.run(cmd, 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE,
                         timeout=10,
                         check=False)
            
            if result.returncode == 0:
                print(f"[TTS] Played successfully")
            else:
                print(f"[TTS] aplay exited with code {result.returncode}")
                if result.stderr:
                    print(f"[TTS] stderr: {result.stderr.decode()}")
            sys.stdout.flush()
                
        except subprocess.TimeoutExpired:
            print(f"[TTS] Playback timed out")
            sys.stdout.flush()
        except Exception as e:
            print(f"[TTS] Error: {e}")
            sys.stdout.flush()
            import traceback
            traceback.print_exc()
        finally:
            # Clean up temp files
            if temp_mp3:
                try:
                    os.unlink(temp_mp3)
                except:
                    pass
            if temp_wav:
                try:
                    os.unlink(temp_wav)
                except:
                    pass
    
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
