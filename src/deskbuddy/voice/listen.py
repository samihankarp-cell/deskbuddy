"""Hold-to-talk: hold the hotkey, speak, let go. Speech is turned into text on this PC."""
import threading

import numpy as np
from PySide6.QtCore import QObject, Signal

from deskbuddy.voice import hotkey as keys

RATE = 16000
MIN_SECONDS = 0.35


class Listener(QObject):
    listening = Signal(bool)   # the key went down / came up
    heard = Signal(str)        # the words that were said
    problem = Signal(str)      # plain-words reason it could not listen
    escape = Signal()          # Esc was pressed anywhere

    def __init__(self, hotkey: str, model_size: str):
        super().__init__()
        self._hotkey = keys.normalize(hotkey)
        self._hook = None
        self._model_size = model_size
        import os

        self._language = os.environ.get("DESKBUDDY_LANGUAGE", "en") or None
        self._model = None
        self._stream = None
        self._chunks: list[np.ndarray] = []
        self._down = False
        self._lock = threading.Lock()

    def start(self) -> None:
        import keyboard

        # One global hook, matched by key name and side (not scan code: left and right Ctrl share one).
        self._hook = keyboard.hook(self._on_key)
        threading.Thread(target=self._load_model, daemon=True, name="buddy-ears").start()

    def set_hotkey(self, name: str) -> None:
        """Use another key from now on, without a restart. The hook reads the key on every event."""
        with self._lock:
            self._hotkey = keys.normalize(name)
            held = self._down
        if held:  # the old key may never come up now: stop recording as if it had
            self._released(None)

    def _on_key(self, event) -> None:
        if keys.is_escape(event):
            if event.event_type == "down":
                self.escape.emit()
        elif keys.matches(event, self._hotkey):
            if event.event_type == "down":
                self._pressed(event)
            else:
                self._released(event)

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        except Exception as error:
            self.problem.emit(f"I couldn't load my hearing: {str(error)[:120]}")

    def _pressed(self, _event) -> None:
        with self._lock:
            if self._down:  # the key repeats while held
                return
            self._down = True
            self._chunks = []
            try:
                import sounddevice as sd

                self._stream = sd.InputStream(
                    samplerate=RATE, channels=1, dtype="float32",
                    callback=lambda data, *_: self._chunks.append(data.copy()),
                )
                self._stream.start()
            except Exception as error:
                self._down = False
                self._stream = None
                self.problem.emit(f"I couldn't use the microphone: {str(error)[:120]}")
                return
        self.listening.emit(True)

    def _released(self, _event) -> None:
        with self._lock:
            if not self._down:
                return
            self._down = False
            stream, self._stream = self._stream, None
            chunks, self._chunks = self._chunks, []
        if stream is not None:
            stream.stop()
            stream.close()
        self.listening.emit(False)
        threading.Thread(target=self._transcribe, args=(chunks,), daemon=True).start()

    def _transcribe(self, chunks: list[np.ndarray]) -> None:
        if not chunks:
            return
        audio = np.concatenate(chunks).flatten()
        if len(audio) < RATE * MIN_SECONDS:
            return  # a tap, not speech
        if self._model is None:
            self.problem.emit("I couldn't hear that because my hearing is still loading. Try again in a moment.")
            return
        try:
            segments, _info = self._model.transcribe(audio, beam_size=3, vad_filter=True, language=self._language)
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as error:
            self.problem.emit(f"I couldn't understand the recording: {str(error)[:120]}")
            return
        if text:
            self.heard.emit(text)
        else:
            self.problem.emit("I couldn't hear any words in that.")
