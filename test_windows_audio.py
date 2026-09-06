"""Exercise Windows audio without devices or third-party imports."""
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch
import wave

from windows_audio import device, play, record
from assistant_backend import Audio


class WindowsAudioChecks(unittest.TestCase):
    def test_device_selection(self):
        for value, expected in [('', None), ('default', None), ('12', 12),
                                ('USB microphone', 'USB microphone')]:
            with patch.dict(os.environ, {'YESMAN_INPUT_DEVICE': value}):
                self.assertEqual(device('YESMAN_INPUT_DEVICE'), expected)

    def test_recording_limit_and_wav_finalization(self):
        audio = MagicMock()
        audio.query_devices.return_value = {'default_samplerate': 16000}
        stream = audio.RawInputStream.return_value.__enter__.return_value
        stream.read.side_effect = lambda frames: (b'\0\0' * frames, False)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'question.wav'
            record(path, threading.Event(), audio)
            with wave.open(str(path), 'rb') as result:
                self.assertEqual(result.getnframes(), 16000 * 30)
                self.assertEqual(result.getsampwidth(), 2)
                self.assertEqual(result.getnchannels(), 1)

    def test_stop_finalizes_partial_recording_and_playback_can_abort(self):
        audio = MagicMock()
        audio.query_devices.return_value = {'default_samplerate': 16000}
        stopped = threading.Event()
        def read(frames):
            stopped.set()
            return b'\0\0' * frames, False
        audio.RawInputStream.return_value.__enter__.return_value.read.side_effect = read
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'question.wav'
            record(path, stopped, audio)
            with wave.open(str(path), 'rb') as result:
                self.assertEqual(result.getnframes(), 800)
            play(path, threading.Event(), audio)
            output = audio.RawOutputStream.return_value.__enter__.return_value
            output.write.assert_called_once_with(b'\0\0' * 800)
            play(path, stopped, audio)
            output.abort.assert_called_once()

    def test_windows_stop_uses_stdin_and_closes_handles(self):
        audio = Audio()
        process = MagicMock()
        process.poll.return_value = None
        process.wait.return_value = 0
        audio.process = process
        try:
            with patch('assistant_backend.sys.platform', 'win32'):
                audio.stop()
                audio.finish()
            process.stdin.write.assert_called_once_with(b'\n')
            process.send_signal.assert_not_called()
            process.stdin.close.assert_called_once()
        finally:
            audio.close()

    def test_failed_windows_capture_is_not_transcribed(self):
        from yesman import Assistant
        app = Assistant(MagicMock())
        try:
            app.status = 'LISTENING'
            app.audio.process = MagicMock()
            app.audio.process.poll.return_value = 1
            app.audio.process.wait.return_value = 1
            with patch('yesman.sys.platform', 'win32'):
                with self.assertRaisesRegex(RuntimeError, 'Recording failed'):
                    app.tick()
            app.api.transcribe.assert_not_called()
            self.assertEqual(app.status, 'READY')
        finally:
            app.close()
