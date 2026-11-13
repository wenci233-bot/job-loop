import json
import threading
import time
import unittest
from concurrent.futures import CancelledError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.services import rank, interview, ai
from server.api.rank import router as rank_router
from server.api.interview import router as interview_router


def until(predicate):
    end = time.monotonic() + 3
    while time.monotonic() < end:
        if predicate(): return
        time.sleep(.01)
    raise AssertionError('worker did not finish')


class TaskStopTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI(); app.include_router(rank_router); app.include_router(interview_router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_batch_keeps_completed_discards_late_and_skips_remaining(self):
        entered, release = threading.Event(), threading.Event()
        calls, writes = [], []
        def evaluate(text, parsed, **kwargs):
            calls.append(text)
            if text == '2':
                entered.set(); release.wait(3)
            return dict(score=80, veto=False, reasons=[])
        with patch.object(rank, 'evaluate', evaluate), patch('server.storage.inbox.get_entry', side_effect=lambda eid: {'company': '公司', 'role': eid}), patch('server.storage.inbox.entry_text', side_effect=lambda eid: eid), patch('server.storage.inbox.update_entry', side_effect=lambda eid, **kw: writes.append(eid)):
            task_id = rank.start_batch(['1', '2', '3'])
            try:
                self.assertTrue(entered.wait(2))
                response = self.client.post(f'/rank/score/batch/{task_id}/stop')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['status'], 'cancelled')
                self.assertEqual(response.json()['done'], 1)
                self.assertEqual(response.json()['ok'], 1)
                self.assertEqual(self.client.post(f'/rank/score/batch/{task_id}/stop').json()['status'], 'cancelled')
            finally: release.set()
            until(lambda: task_id not in rank._BATCH_CANCEL)
            self.assertEqual(writes, ['1']); self.assertEqual(calls, ['1', '2'])
            self.assertEqual(rank.get_batch_task(task_id)['status'], 'cancelled')

    def test_cancelled_prep_preserves_old_file_and_allows_restart(self):
        entered, release = threading.Event(), threading.Event()
        with TemporaryDirectory() as tmp, patch.object(interview, '_archive', return_value=Path(tmp)):
            path = Path(tmp) / 'prep.json'; path.write_text('{"old": true}')
            def generate(*args, **kwargs):
                self.assertFalse(kwargs['persist'])
                entered.set(); release.wait(3)
                return {'questions': [{'question': 'new'}]}
            with patch.object(interview, 'generate_prep', generate):
                tid = interview.start_generation('公司', '岗位')
                try:
                    self.assertTrue(entered.wait(2))
                    self.assertEqual(self.client.post(f'/interview/generate/task/{tid}/stop').json()['status'], 'cancelled')
                finally: release.set()
                until(lambda: tid not in interview._GEN_CANCEL)
            self.assertEqual(json.loads(path.read_text()), {'old': True})
            with patch.object(interview, 'generate_prep', return_value={'questions': [1, 2]}):
                new = interview.start_generation('公司', '岗位')
                until(lambda: new not in interview._GEN_CANCEL)
            self.assertEqual(interview.stop_generation(new)['status'], 'done')
            self.assertEqual(json.loads(path.read_text())['questions'], [1, 2])

    def test_cancellation_never_falls_back_to_heuristic(self):
        with patch.object(rank, 'load_candidate', return_value={}), patch.object(rank, '_ai_evaluate', side_effect=CancelledError()), patch.object(rank, '_heuristic') as fallback:
            with self.assertRaises(CancelledError): rank.evaluate('正常岗位')
            fallback.assert_not_called()
        event = threading.Event(); event.set()
        with patch.object(ai.urllib.request, 'urlopen') as request:
            with self.assertRaises(CancelledError): ai.chat([], cancel_event=event)
            request.assert_not_called()

    def test_unknown_stop_returns_404(self):
        for path in ['/rank/score/batch/missing/stop', '/interview/generate/task/missing/stop']:
            self.assertEqual(self.client.post(path).status_code, 404)
