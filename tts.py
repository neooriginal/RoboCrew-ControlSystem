"""Text-to-Speech module using gTTS."""

import threading
import queue
import tempfile
import os
import subprocess
from gtts import gTTS
from config import TTS_ENABLED, TTS_AUDIO_DEVICE, TTS_TLD, TTS_VOLUME_BOOST

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


class TTSEngine:
    def __init__(self):
        self.enabled = TTS_ENABLED
        self.audio_device = TTS_AUDIO_DEVICE
        self.tld = TTS_TLD
        self.volume_boost = TTS_VOLUME_BOOST
        self.speech_queue = queue.Queue()
        self.worker_thread = None
        
        if self.enabled:
            self.audio_player = self._find_audio_player()
            if self.audio_player:
                self.worker_thread = threading.Thread(target=self._worker, daemon=True)
                self.worker_thread.start()
                print(f"[TTS] Initialized with Google voices (using {self.audio_player})")
            else:
                print("[TTS] No audio player found")
                self.enabled = False
        else:
            print("[TTS] TTS disabled in config")
    
    def _find_audio_player(self):
        """Find available audio player."""
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
        """Background worker processing speech queue."""
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
    
    def _detect_language(self, text):
        """Auto-detect language, fallback to English."""
        if not LANGDETECT_AVAILABLE:
            return 'en'
        
        try:
            lang = detect(text)
            return lang if lang else 'en'
        except:
            return 'en'
    
    def _speak_blocking(self, text):
        """Generate and play speech."""
        import sys
        temp_mp3 = None
        temp_wav = None
        temp_wav_boosted = None
        
        try:
            lang = self._detect_language(text)
            print(f"[TTS] Speaking ({lang}): '{text}'")
            sys.stdout.flush()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_mp3 = fp.name
            
            tts = gTTS(text=text, lang=lang, tld=self.tld, slow=False, timeout=5)
            tts.save(temp_mp3)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as fp:
                temp_wav = fp.name
            
            # Decode MP3 to WAV
            result = subprocess.run(['mpg123', '-w', temp_wav, temp_mp3], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL,
                         timeout=5)
            
            if result.returncode != 0:
                print(f"[TTS] MP3 decode failed")
                sys.stdout.flush()
                return
            
            # Try to amplify with sox if available, otherwise use original WAV
            audio_to_play = temp_wav
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='_boost.wav') as fp:
                    temp_wav_boosted = fp.name
                
                result = subprocess.run(['sox', temp_wav, temp_wav_boosted, 'gain', str(self.volume_boost)], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             timeout=2,
                             check=False)
                
                if result.returncode == 0:
                    audio_to_play = temp_wav_boosted
                    print(f"[TTS] Amplified +{self.volume_boost}dB")
                    sys.stdout.flush()
            except FileNotFoundError:
                print(f"[TTS] sox not installed, playing without boost")
                sys.stdout.flush()
            except Exception as e:
                print(f"[TTS] sox failed: {e}")
                sys.stdout.flush()
            
            # Play audio
            print(f"[TTS] Playing: {audio_to_play}")
            sys.stdout.flush()
            
            result = subprocess.run(['aplay', '-D', self.audio_device, audio_to_play], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE,
                         timeout=10,
                         check=False)
            
            if result.returncode == 0:
                print(f"[TTS] ✓")
            else:
                print(f"[TTS] aplay failed: {result.returncode}")
                if result.stderr:
                    print(f"[TTS] stderr: {result.stderr.decode()}")
            sys.stdout.flush()
                
        except subprocess.TimeoutExpired:
            print(f"[TTS] Timeout")
            sys.stdout.flush()
        except Exception as e:
            print(f"[TTS] Error: {e}")
            sys.stdout.flush()
        finally:
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
            if temp_wav_boosted:
                try:
                    os.unlink(temp_wav_boosted)
                except:
                    pass
    
    def speak(self, text):
        """Queue text for speech."""
        if self.enabled and text:
            self.speech_queue.put(text)
    
    def shutdown(self):
        """Shutdown TTS engine."""
        if self.worker_thread:
            self.speech_queue.put(None)
            self.worker_thread.join(timeout=2)


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
