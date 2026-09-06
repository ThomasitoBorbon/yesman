"""OpenAI adapter and Linux/Windows audio process management."""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path


class API:
    def __init__(self, key):
        self.key = key
        self.history = []

    def request(self, endpoint, body, content_type='application/json'):
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        request = urllib.request.Request(
            'https://api.openai.com/v1/' + endpoint, data=body,
            headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            # Do not echo server responses or credentials into the terminal.
            hints = {401: 'Check your API key.', 429: 'Check API quota or try again later.'}
            raise RuntimeError(f'API error {error.code}. ' + hints.get(error.code, 'Please try again.')) from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError('API connection failed or timed out. Check your network.') from None

    def reply(self, message):
        pending = self.history[-20:] + [{'role': 'user', 'content': message}]
        result = json.loads(self.request('responses', {
            'model': os.getenv('YESMAN_MODEL', 'gpt-5.5'),
            'instructions': 'You are a cheerful personal assistant called Yes Man. '
                            'Be warm, helpful, and honest, including when you disagree. '
                            'Keep replies concise and easy to speak aloud. Use plain text.',
            'input': pending,
            'store': False,
        }))
        answer = '\n'.join(part['text'] for item in result.get('output', [])
                           if item.get('type') == 'message'
                           for part in item.get('content', [])
                           if part.get('type') == 'output_text').strip()
        if not answer:
            raise RuntimeError('No text response returned. Please try again.')
        self.history = pending + [{'role': 'assistant', 'content': answer}]
        return answer

    def transcribe(self, path):
        boundary = uuid.uuid4().hex
        model = os.getenv('YESMAN_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe')
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n'
                f'{model}\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                'filename="question.wav"\r\nContent-Type: audio/wav\r\n\r\n').encode()
        body += Path(path).read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
        text = json.loads(self.request('audio/transcriptions', body,
                         'multipart/form-data; boundary=' + boundary)).get('text', '').strip()
        if not text:
            raise RuntimeError('No speech recognized. Please try again.')
        return text

    def speech(self, text):
        return self.request('audio/speech', {
            'model': os.getenv('YESMAN_TTS_MODEL', 'gpt-4o-mini-tts'),
            'voice': os.getenv('YESMAN_VOICE', 'cedar'),
            'input': text,
            'instructions': 'Speak warmly and cheerfully, with an eager, lightly robotic delivery.',
            'response_format': 'wav',
        })


class Audio:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='yesman-')
        self.recording = Path(self.directory.name) / 'question.wav'
        self.playback = Path(self.directory.name) / 'answer.wav'
        self.process = None
        self.errors = None

    def start(self, command):
        windows = sys.platform == 'win32'
        if not shutil.which(command[0]):
            raise RuntimeError(f'{command[0]} is missing. Install alsa-utils for voice support.')
        self.errors = tempfile.TemporaryFile()
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE if windows else subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL, stderr=self.errors,
                                            **({'creationflags': subprocess.CREATE_NO_WINDOW} if windows else {}))
        except Exception:
            self.errors.close()
            self.errors = None
            raise

    def record(self):
        self.recording.unlink(missing_ok=True)
        if sys.platform == 'win32':
            self.start_windows('record', self.recording)
            return
        self.start(['arecord', '-q', '-D', os.getenv('YESMAN_INPUT_DEVICE', 'default'),
                    '-t', 'wav', '-f', 'S16_LE', '-r', '16000', '-c', '1', '-d', '30',
                    str(self.recording)])

    def stop(self):
        if self.process and self.process.poll() is None:
            if sys.platform == 'win32':
                try:
                    self.process.stdin.write(b'\n')
                    self.process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
            else:
                self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def finish(self):
        code = self.process.wait() if self.process else 0
        if self.process and self.process.stdin:
            self.process.stdin.close()
        self.process = None
        if self.errors:
            self.errors.close()
            self.errors = None
        return code

    def validate_recording(self):
        try:
            with wave.open(str(self.recording), 'rb') as recording:
                if recording.getnframes() < recording.getframerate() // 4:
                    raise ValueError()
        except (OSError, EOFError, wave.Error, ValueError):
            raise RuntimeError('No usable recording. Check your microphone and input device.') from None

    def play(self, data):
        self.playback.write_bytes(data)
        if sys.platform == 'win32':
            self.start_windows('play', self.playback)
            return
        self.start(['aplay', '-q', '-D', os.getenv('YESMAN_OUTPUT_DEVICE', 'default'),
                    str(self.playback)])

    def start_windows(self, mode, path):
        # Check in the parent so a missing dependency gives an actionable message.
        try:
            import sounddevice  # noqa: F401
        except (ImportError, OSError):
            raise RuntimeError('Windows voice requires sounddevice. Run: '
                               'python -m pip install -r requirements.txt') from None
        self.start([sys.executable, str(Path(__file__).with_name('windows_audio.py')),
                    mode, str(path)])

    def close(self):
        self.stop()
        self.finish()
        self.directory.cleanup()
