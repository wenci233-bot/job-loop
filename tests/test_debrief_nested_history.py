import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from server.services import debrief, interview


class NestedHistoryTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for module in (debrief, interview):
            for name, value in [('APPLICATIONS_DIR', self.root), ('ensure_dirs', lambda: None)]:
                mock = patch.object(module, name, value)
                mock.start()
                self.addCleanup(mock.stop)
        self.company = '商汤科技'
        self.role = '算法工程师（Agent/RAG方向）'
        self.history = [{'role': 'interviewer', 'text': '如何评估检索？'},
                        {'role': 'candidate', 'text': '比较召回率'}]
        self.report = {'overall': 46, 'per_question': [
            {'question': '如何评估检索？', 'score': 30, 'verdict': '需改进'}]}

    def test_nested_backfill_dedup_and_learning_context(self):
        session = interview.save_mock(self.company, self.role, self.history, self.report)
        for _ in range(2):
            result = debrief.list_history()
            self.assertEqual(result['sync_warnings'], [])
            self.assertEqual(len(result['rounds']), 1)
            row = result['rounds'][0]
            self.assertEqual(row['source_session_id'], session['id'])
            self.assertEqual(row['company_role'], self.company + '_' + self.role)
            self.assertEqual(row['mock_history'], self.history)
        self.assertTrue((self.root / row['company_role'] / 'debrief.json').exists())
        self.assertIn('如何评估检索', debrief._past_text())
        self.assertEqual(len(debrief.all_stuck_points()), 1)
        self.assertTrue(debrief.delete_round(row['company_role'], row['id']))
        self.assertEqual(debrief.list_history()['rounds'], [])
        self.assertEqual(len(interview.list_mocks(self.company, self.role)), 1)

    def test_already_imported_nested_record_not_duplicated(self):
        session = interview.save_mock(self.company, self.role, self.history, self.report)
        debrief.import_mock(self.company, self.role, session['id'])
        self.assertEqual(len(debrief.list_history()['rounds']), 1)

    def test_legacy_nested_record_without_company_and_role(self):
        session = interview.save_mock(self.company, self.role, self.history, self.report)
        path = interview._mock_path(self.company, self.role)
        data = json.loads(path.read_text())
        del data['sessions'][0]['company']
        del data['sessions'][0]['role']
        path.write_text(json.dumps(data))
        row = debrief.list_history()['rounds'][0]
        self.assertEqual((row['company'], row['role']), (self.company, self.role))

    def test_deletion_rejects_escape_and_absolute_paths(self):
        for archive in ('../outside', str(self.root), str(self.root / 'child'), 'child/../../outside'):
            with self.assertRaises(ValueError):
                debrief.delete_round(archive, 'missing')


if __name__ == '__main__':
    unittest.main()
