"""Windows audio worker; a newline on stdin requests graceful shutdown."""
import os
import sys
import threading
import wave


def device(name):
    value = os.getenv(name, '').strip()
    if not value or value == 'default':
        return None
    return int(value) if value.isdecimal() else value


def record(path, stopped, audio):
    selected = device('YESMAN_INPUT_DEVICE')
    rate = int(audio.query_devices(selected, 'input')['default_samplerate'])
    block = max(1, rate // 20)
    with wave.open(str(path), 'wb') as target:
        target.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        with audio.RawInputStream(samplerate=rate, channels=1, dtype='int16',
                                  device=selected) as stream:
            remaining = rate * 30
            while remaining and not stopped.is_set():
                frames = min(block, remaining)
                data, overflow = stream.read(frames)
                if overflow:
                    raise RuntimeError('Microphone buffer overflow. Try another input device.')
                target.writeframesraw(data)
                remaining -= frames


def play(path, stopped, audio):
    with wave.open(str(path), 'rb') as source:
        if source.getsampwidth() != 2:
            raise RuntimeError('Playback requires 16-bit PCM WAV audio.')
        rate = source.getframerate()
        with audio.RawOutputStream(samplerate=rate, channels=source.getnchannels(),
                                   dtype='int16', device=device('YESMAN_OUTPUT_DEVICE')) as stream:
            while not stopped.is_set():
                data = source.readframes(max(1, rate // 20))
                if not data:
                    break
                stream.write(data)
            if stopped.is_set():
                stream.abort()


def main():
    import sounddevice

    stopped = threading.Event()

    def listen():
        sys.stdin.buffer.readline()
        stopped.set()

    threading.Thread(target=listen, daemon=True).start()
    action = {'record': record, 'play': play}[sys.argv[1]]
    action(sys.argv[2], stopped, sounddevice)


if __name__ == '__main__':
    main()
