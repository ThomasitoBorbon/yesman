"""Clock-driven terminal animation; no audio or network dependencies."""


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
        opening = (0, 1, 3, 2, 1, 0, 2, 3)[int(now * 9) % 8]
        for y in range(18, 24):
            replace(y, 17, 38, ' ' * 21 if y < 18 + opening else '')
    return rows
