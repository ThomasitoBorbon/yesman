"""Offline terminal layout preview. Run with: python3 preview.py"""

import curses
import locale
import textwrap
from pathlib import Path


def load_face():
    lines = Path(__file__).with_name('assets').joinpath('yesman.txt').read_text().splitlines()
    # Remove only the uninterrupted background, retaining every feature row.
    while lines and not lines[0].strip('█'):
        lines.pop(0)
    while lines and not lines[-1].strip('█'):
        lines.pop()
    width = max(map(len, lines))
    return ['█' * width] + [line.ljust(width, '█') for line in lines] + ['█' * width]


def run(screen):
    curses.curs_set(1)
    screen.keypad(True)
    face = load_face()
    draft = ''
    answer = 'Hello! This is the offline Yes Man display preview. Type a message to try the layout.'
    offset = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        h, w = min(height, 48), min(width, 90)
        left = max(0, (width - w) // 2)

        def put(y, x, value, style=0):
            if 0 <= y < height and 0 <= x < width - 1:
                screen.addnstr(y, x, value, max(0, width - x - 1), style)

        if h < 40 or w < 60:
            put(0, 0, 'Resize terminal to at least 60 columns x 40 rows.')
            put(1, 0, 'Target: 90 columns x 48 rows. Esc exits.')
            screen.refresh()
            key = screen.get_wch()
            if key == '\x1b':
                return
            continue

        put(0, left, 'YES MAN  |  OFFLINE DEMO', curses.A_BOLD)
        for row, line in enumerate(face, 2):
            put(row, left + (w - len(line)) // 2, line)
        divider = len(face) + 3
        put(divider, left, '─' * (w - 1))
        put(divider + 1, left, 'RESPONSE', curses.A_BOLD)
        lines = []
        for paragraph in answer.splitlines():
            lines.extend(textwrap.wrap(paragraph, w - 2) or [''])
        capacity = h - divider - 6
        offset = min(offset, max(0, len(lines) - capacity))
        for i, line in enumerate(lines[offset:offset + capacity]):
            put(divider + 2 + i, left, line)
        put(h - 3, left, 'Enter: send  |  PgUp/PgDn: response  |  Esc: exit', curses.A_DIM)
        put(h - 2, left, 'YOU > ', curses.A_BOLD)
        visible = draft[-(w - 9):]
        put(h - 2, left + 6, visible)
        screen.move(h - 2, left + 6 + len(visible))
        screen.refresh()
        key = screen.get_wch()
        if key == '\x1b':
            return
        if key in ('\n', '\r', curses.KEY_ENTER):
            if draft.strip().lower() in ('/exit', '/quit'):
                return
            if draft.strip():
                answer = ('You said: ' + draft.strip() + '\n\n'
                          'Absolutely! The face stays in place while this response changes. '
                          'This is a canned demo response; no AI request was sent. '
                          'We can connect the existing chatbot after checking the screen layout.')
                draft, offset = '', 0
        elif key in (curses.KEY_BACKSPACE, '\x7f', '\b'):
            draft = draft[:-1]
        elif key == curses.KEY_PPAGE:
            offset = max(0, offset - capacity)
        elif key == curses.KEY_NPAGE:
            offset = min(max(0, len(lines) - capacity), offset + capacity)
        elif isinstance(key, str) and key.isprintable() and key.isascii():
            draft += key


if __name__ == '__main__':
    locale.setlocale(locale.LC_ALL, '')
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
