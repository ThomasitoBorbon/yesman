"""Yes Man terminal assistant: demo by default, --live for API chat and voice."""
import argparse
import curses
import getpass
import locale
import os
import queue
import sys
import textwrap
import threading
import time
import unicodedata

from assistant_backend import API, Audio
from preview import load_face
from animation import ResponseAnimation, animate_face


def display_text(value):
    # Keep remote text from injecting terminal controls; use single-cell glyphs.
    return ''.join(c if c == '\n' or (c.isprintable() and
                   not unicodedata.combining(c) and unicodedata.east_asian_width(c) not in 'WF')
                   else ' ' for c in value)


class Assistant:
    def __init__(self, api=None):
        self.api = api
        self.audio = Audio()
        self.events = queue.Queue()
        self.closed = threading.Event()
        self.status = 'READY'
        self.speak = True
        self.answer = ('Hello! Type a question or press F2 to record. My voice is AI-generated.'
                       if api else 'Offline demo: type a message to test the face and text layout. '
                       'Start with --live to enable API chat and voice.')
        self.heard = ''

    def work(self, function, event):
        def worker():
            try:
                result = function()
                if not self.closed.is_set():
                    self.events.put((event, result))
            except Exception as error:
                if not self.closed.is_set():
                    self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def send(self, message):
        self.heard = message
        if self.api:
            self.status = 'THINKING'
            self.work(lambda: self.api.reply(message), 'answer')
        else:
            self.answer = 'You said: ' + message + '\n\nAbsolutely! This is a demo reply. No API request was sent.'

    def record_toggle(self):
        if not self.api:
            self.answer = 'Voice is available in live mode: python yesman.py --live'
        elif self.status == 'LISTENING':
            self.audio.stop()
        elif self.status == 'READY':
            self.audio.record()
            self.status = 'LISTENING'

    def tick(self):
        if self.audio.process and self.audio.process.poll() is not None:
            code = self.audio.finish()
            if self.status == 'LISTENING':
                self.status = 'READY'
                if sys.platform == 'win32' and code:
                    raise RuntimeError('Recording failed. Check Windows microphone permissions '
                                       'and your input device.')
                self.audio.validate_recording()
                self.status = 'TRANSCRIBING'
                self.work(lambda: self.api.transcribe(self.audio.recording), 'transcript')
            elif self.status == 'SPEAKING':
                self.status = 'READY'
                if code:
                    self.speech_chunks = None
                    self.answer += '\n\nPlayback failed. Check your output device. Text chat still works.'
        while not self.events.empty():
            event, value = self.events.get_nowait()
            if event == 'error':
                self.speech_chunks = None
                self.answer += '\n\n' + value
                self.status = 'READY'
            elif event == 'transcript':
                self.send(value)
            elif event == 'answer':
                self.answer = value
                self.status = 'READY'
                if self.speak:
                    self.status = 'GENERATING VOICE'
                    # Split at a conservative character count to fit speech input limits.
                    chunks = textwrap.wrap(value, 1800, replace_whitespace=False)
                    self.speech_chunks = iter(chunks)
                    self.next_speech()
            elif event == 'audio':
                self.status = 'READY'
                if self.speak:
                    self.audio.play(value)
                    self.status = 'SPEAKING'
        if self.status == 'READY' and self.speak and getattr(self, 'speech_chunks', None):
            self.next_speech()

    def next_speech(self):
        chunk = next(self.speech_chunks, None)
        if chunk:
            self.status = 'GENERATING VOICE'
            self.work(lambda: self.api.speech(chunk), 'audio')
        else:
            self.speech_chunks = None
            self.status = 'READY'

    def toggle_speech(self):
        self.speak = not self.speak
        if not self.speak:
            self.speech_chunks = None
            if self.status == 'SPEAKING':
                self.audio.stop()
                self.audio.finish()
                self.status = 'READY'

    def close(self):
        self.closed.set()
        self.audio.close()


def run(screen, app):
    curses.curs_set(1)
    screen.keypad(True)
    screen.timeout(33)
    face = load_face()
    animation = ResponseAnimation()
    follow = True
    draft, offset = '', 0
    while True:
        try:
            app.tick()
        except Exception as error:
            app.answer += '\n\n' + str(error)
            app.speech_chunks = None
            app.status = 'READY'
        now = time.monotonic()
        if animation.update(display_text(app.answer), now):
            offset, follow = 0, True
        screen.erase()
        height, width = screen.getmaxyx()
        h, w = min(height, 48), min(width, 90)
        left = max(0, (width - w) // 2)

        def put(y, x, value, style=0):
            if 0 <= y < height and 0 <= x < width - 1:
                try:
                    screen.addnstr(y, x, value, min(w - 1, width - x - 1), style)
                except curses.error:
                    pass  # Terminal may resize between measuring and drawing.

        capacity, lines = 1, []
        if h < 40 or w < 60:
            put(0, 0, 'Resize to 90 columns x 48 rows (minimum 60 x 40).')
            put(1, 0, 'Esc: exit | F2: stop recording')
        else:
            mode = 'LIVE' if app.api else 'DEMO'
            put(0, left, f'YES MAN | {mode} | {app.status} | Voice {"ON" if app.speak else "OFF"}', curses.A_BOLD)
            shown = animation.visible(now)
            speaking = app.status == 'SPEAKING' or (not app.api and shown != animation.text)
            for row, line in enumerate(animate_face(face, now, speaking), 2):
                put(row, left + (w - len(line)) // 2, line)
            divider = len(face) + 3
            put(divider, left, '─' * (w - 1))
            put(divider + 1, left, ('YOU: ' + display_text(app.heard))[:w - 1], curses.A_DIM)
            for paragraph in shown.splitlines():
                lines.extend(textwrap.wrap(paragraph, w - 2) or [''])
            capacity = h - divider - 7
            offset = max(0, len(lines) - capacity) if follow else min(offset, max(0, len(lines) - capacity))
            for i, line in enumerate(lines[offset:offset + capacity]):
                put(divider + 2 + i, left, line)
            put(h - 4, left, 'F2: record/stop (30s max) | F3: voice on/off', curses.A_DIM)
            put(h - 3, left, 'Enter: send | F4: show all | PgUp/Dn: scroll | Esc: exit', curses.A_DIM)
            visible = draft[-(w - 9):]
            put(h - 2, left, 'YOU > ' + visible)
            screen.move(h - 2, left + 6 + len(visible))
        screen.refresh()
        try:
            key = screen.get_wch()
        except curses.error:
            continue
        if key == '\x1b':
            return
        try:
            if key == curses.KEY_F2:
                app.record_toggle()
            elif key == curses.KEY_F3:
                app.toggle_speech()
            elif key == curses.KEY_F4:
                animation.reveal()
            elif key in ('\n', '\r', curses.KEY_ENTER):
                if draft.strip().lower() in ('/exit', '/quit'):
                    return
                if draft.strip() and app.status == 'READY':
                    app.send(draft.strip())
                    draft = ''
            elif key in (curses.KEY_BACKSPACE, '\x7f', '\b'):
                draft = draft[:-1]
            elif key == curses.KEY_PPAGE:
                follow = False
                offset = max(0, offset - capacity)
            elif key == curses.KEY_NPAGE:
                offset = min(max(0, len(lines) - capacity), offset + capacity)
                follow = offset == max(0, len(lines) - capacity)
            elif isinstance(key, str) and key.isascii() and key.isprintable():
                draft += key
        except Exception as error:
            app.answer += '\n\n' + str(error)
            app.status = 'READY'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Enable paid API chat and voice')
    args = parser.parse_args()
    api = None
    if args.live:
        key = os.getenv('OPENAI_API_KEY') or getpass.getpass('OpenAI API key (hidden, not saved): ')
        if not key.strip():
            parser.error('An API key is required for live mode.')
        api = API(key.strip())
    locale.setlocale(locale.LC_ALL, '')
    app = Assistant(api)
    try:
        curses.wrapper(run, app)
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == '__main__':
    main()
