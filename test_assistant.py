"""Offline integration checks; no microphone use or API charges."""
import json
import unittest
from unittest.mock import Mock

from assistant_backend import API
from yesman import Assistant, display_text


class Checks(unittest.TestCase):
    def test_failed_request_does_not_poison_history(self):
        api = API('test')
        api.request = Mock(side_effect=RuntimeError('offline'))
        with self.assertRaises(RuntimeError):
            api.reply('hello')
        self.assertEqual(api.history, [])
        api.request = Mock(return_value=json.dumps({'output': [
            {'type': 'reasoning'}, {'type': 'message', 'content': [
                {'type': 'output_text', 'text': 'Hello!'}]}]}).encode())
        self.assertEqual(api.reply('retry'), 'Hello!')
        self.assertEqual([turn['content'] for turn in api.history], ['retry', 'Hello!'])

    def test_voice_and_text_share_conversation_and_mute(self):
        app = Assistant(Mock())
        app.work = lambda function, event: app.events.put((event, function()))
        app.audio.play = Mock()
        app.api.reply.return_value = 'Hello there.'
        app.api.speech.return_value = b'wav'
        try:
            app.events.put(('transcript', 'spoken question'))
            app.tick()
            app.api.reply.assert_called_once_with('spoken question')
            app.audio.play.assert_called_once_with(b'wav')
            self.assertEqual(app.answer, 'Hello there.')
            app.toggle_speech()
            self.assertEqual(app.status, 'READY')
            app.send('typed follow-up')
            app.tick()
            self.assertEqual(app.api.reply.call_count, 2)
            self.assertEqual(app.api.speech.call_count, 1)
        finally:
            app.close()

    def test_speech_failure_preserves_answer_and_recovers(self):
        app = Assistant(Mock())
        try:
            app.answer = 'Useful answer.'
            app.status = 'GENERATING VOICE'
            app.speech_chunks = iter(['must not send'])
            app.events.put(('error', 'Speech failed'))
            app.tick()
            self.assertIn('Useful answer.', app.answer)
            self.assertEqual(app.status, 'READY')
            self.assertIsNone(app.speech_chunks)
        finally:
            app.close()

    def test_terminal_controls_removed(self):
        self.assertNotIn('\x1b', display_text('hello\x1b[2J'))


if __name__ == '__main__':
    unittest.main()
