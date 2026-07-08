import io
import wave

import numpy as np
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000


class Recorder:
    """Records mic audio on a background stream from start() until stop()."""

    def __init__(self, samplerate=SAMPLE_RATE):
        self.samplerate = samplerate
        self._frames = []
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def start(self):
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate, channels=1, dtype='int16', callback=self._callback
        )
        self._stream.start()

    def stop(self):
        """Stop the stream and return the recording as WAV bytes."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return b''
        audio = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()


class TranscriptionError(RuntimeError):
    """Raised when audio can't be turned into text - empty recording, no
    recognizable speech, or the (free, keyless) Google Web Speech API being
    unreachable."""


def transcribe(wav_bytes):
    """Transcribe WAV bytes to text using the free Google Web Speech API."""
    if not wav_bytes:
        raise TranscriptionError("No audio was recorded.")
    recognizer = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        raise TranscriptionError("Could not make out any speech - try again, closer to the mic.")
    except sr.RequestError as error:
        raise TranscriptionError(f"Speech recognition service unavailable: {error}")
