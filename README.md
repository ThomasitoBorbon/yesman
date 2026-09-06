# Yes Man for Windows

Use Python 3.12 or 3.13 (64-bit) in Windows Terminal with PowerShell.
Clone or copy the entire repository, including `assets`, then run from its folder:

```powershell
git switch Windows
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe yesman.py
# Live text and voice (paid API usage):
.\.venv\Scripts\python.exe yesman.py --live
# Offline layout preview:
.\.venv\Scripts\python.exe preview.py
```

These commands do not require activating the virtual environment or changing
PowerShell's execution policy. Resize the terminal to 90 columns × 48 rows and
use a monospace font with block-drawing characters, such as Consolas.
Run inside a terminal, rather than IDLE or an editor's output panel.

Windows uses [windows-curses](https://pypi.org/project/windows-curses/) for the UI
and [sounddevice](https://python-sounddevice.readthedocs.io/en/latest/) for audio.
The Windows pip installation includes PortAudio; ALSA tools are unnecessary.
Enable microphone access for desktop apps in Windows Settings and select your
microphone and speakers in Sound settings. F2 starts/stops recording, F3 mutes
spoken replies, and F4 reveals all text. Some laptop keyboards require Fn with
function keys.

To list audio devices and optionally override the Windows defaults:

```powershell
.\.venv\Scripts\python.exe -m sounddevice
$env:YESMAN_INPUT_DEVICE = "1"
$env:YESMAN_OUTPUT_DEVICE = "3"
```

Replace these example indices with devices from your list; a device-name substring
also works. Unset the variables or use `default` to use system defaults. Device
indices can change when hardware is reconnected. Recording uses the microphone's
default sample rate and stops after 30 seconds. Voice errors leave text chat usable.
The live-mode hidden API-key prompt works without storing the key in a file.

## Terminal preview (Linux)


Run in a UTF-8 terminal with a monospace font:

```sh
cd /path/to/yesman
python3 preview.py
```

Designed for **90 columns × 48 rows** (`stty size` reports `48 90`).
The preview uses Python's standard-library curses module and makes no API calls.
It accepts ASCII keyboard input and shows canned responses. Enter sends;
Page Up/Down scroll the response; Escape or `/exit` exits.

The face remains fixed. Solid background rows are trimmed for display; the
original artwork is copied unchanged into `assets/yesman.txt`. Smaller terminals
down to 60 × 40 are supported; below that a resize prompt appears.

## Text and voice assistant

```sh
python3 yesman.py         # Offline text demo
python3 yesman.py --live  # Live text and voice (paid API usage)
```

Live mode reads `OPENAI_API_KEY`, or prompts for a hidden key without saving it.
On Linux it uses only the Python standard library; no pip packages are required.
Linux audio uses `arecord` and `aplay` from `alsa-utils` (already on this VM).
On Raspberry Pi OS, install them if needed with `sudo apt install alsa-utils`.
Use a UTF-8 terminal and a connected microphone and speaker.

- Type and press Enter to send. Drafting is allowed while busy; send when READY.
- F2 starts recording; F2 again stops and submits. Recordings stop at 30 seconds.
- F3 toggles spoken replies and stops current playback. Text replies remain visible.
- Replies appear with a typewriter effect and automatically scroll as text arrives.
  F4 reveals the entire reply immediately. Page Up pauses automatic scrolling;
  Page Down to the bottom resumes it.
- The face blinks and animates its mouth during audio playback. Offline demo
  replies also animate while text appears. Mouth movement is a timed animation,
  not phoneme lip sync; text reveals at 45 characters per second independently
  of speech. Live spoken replies remain enabled by default.
- Page Up/Down scrolls replies. Escape or `/exit` exits.

This is push-to-talk voice, not an always-listening or interruptible realtime call.
Speech is AI-generated using a stock voice. Audio is sent for transcription,
then the question enters the same conversation as typed input. Replies are
displayed and synthesized into speech when enabled. API charges apply to
transcription, chat, and speech generation. An in-flight request may finish even
if you mute or exit; further requests are not scheduled after exit.

The app retains the latest 10 completed conversation turns in memory. It does
not save conversation history or API keys. Temporary WAV files are removed on
normal exit.

Optional environment variables:

| Variable | Default |
| --- | --- |
| `YESMAN_MODEL` | `gpt-5.5` (from your original chatbot) |
| `YESMAN_TRANSCRIBE_MODEL` | `gpt-4o-mini-transcribe` |
| `YESMAN_TTS_MODEL` | `gpt-4o-mini-tts` |
| `YESMAN_VOICE` | `cedar` |
| `YESMAN_INPUT_DEVICE` | `default` |
| `YESMAN_OUTPUT_DEVICE` | `default` |

On Linux, use `arecord -L` and `aplay -L` to list ALSA device names if the default device
does not work. SSH does not forward microphone or speaker audio: the app uses
audio devices on the machine where it runs.

Copy this entire directory, including `animation.py` and `assets`, to the Pi. Launch `yesman.py`
from the Pi's terminal. Keep credentials out of the copied project directory.

API references: [transcription](https://developers.openai.com/api/docs/guides/speech-to-text),
[speech](https://developers.openai.com/api/docs/guides/text-to-speech), and
[text responses](https://developers.openai.com/api/docs/guides/text).

## Verification

Run `python -m unittest discover -v` for offline checks (no API or audio hardware
required). CI runs these checks on Windows and Linux. For a Windows hardware
smoke test, launch the preview, resize the terminal, type a demo message, and
check F4 and scrolling. In live mode, check F2 recording, automatic stop after
30 seconds, F3 during playback, and Escape while recording. Live checks incur
API charges and require a microphone, speakers, and an API key.
