"""Clock-driven terminal animation; no audio or network dependencies."""
import math


class ResponseAnimation:
    def __init__(self):
        self.text = ''
        self.started = 0.0
        self.complete = False

    def update(self, text, now):
        if text != self.text:
            self.text, self.started, self.complete = text, now, False
            return True
        return False

    def visible(self, now):
        count = len(self.text) if self.complete else int(max(0, now - self.started) * 45)
        return self.text[:count]

    def reveal(self):
        self.complete = True


def animate_face(face, now, speaking=False):
    """Animate the bundled artwork, keeping its dimensions and original intact."""
    rows = list(face)
    if len(rows) != 27 or min(map(len, rows)) < 48:
        return rows

    def replace(y, left, right, value):
        rows[y] = rows[y][:left] + value.ljust(right - left, '█') + rows[y][right:]

    if now % 4.8 < 0.18:
        for y in range(8, 12):
            for left, right in ((16, 21), (32, 37)):
                replace(y, left, right, '     ' if y == 10 else '')
    if speaking:
        # Keep the wide smile and its corners fixed. Move only the lower jaw,
        # with a curved outline instead of switching rectangular cutouts.
        # Two smooth rhythms give short closures between larger syllables.
        pulse = (0.5 + 0.5 * math.sin(now * math.tau * 2.6)) ** 1.4
        emphasis = 0.75 + 0.25 * math.sin(now * math.tau * 0.7)
        depth = 1.5 + 6.5 * pulse * emphasis
        for y in range(18, 26):
            cells = []
            for x in range(7, 47):
                horizontal = (x + 0.5 - 27) / 20
                edge = depth * math.sqrt(max(0, 1 - horizontal ** 2))
                coverage = max(0, min(1, edge - (y - 18)))
                # Half-cell edges soften the jaw's vertical motion in a
                # character grid. The lower half block leaves the top open.
                cells.append(' ' if coverage >= 0.75 else '▄' if coverage >= 0.25 else '█')
            replace(y, 7, 47, ''.join(cells))
    return rows
