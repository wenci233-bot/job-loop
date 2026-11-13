import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.services import interview


class InterviewCandidateTests(unittest.TestCase):
    def test_candidates_and_applications_merge_without_duplicates_or_mutation(self):
        applications = [{'company': '甲', 'role': '验证', 'status': '已申请'}]
        candidates = [
            {'id': '1', 'company': '甲', 'role': '验证', 'status': '已评估'},
            {'id': '2', 'company': '乙', 'role': '工艺', 'status': '待评估'},
            {'id': '3', 'company': '乙', 'role': '设备', 'status': '已否决'},
        ]
        with tempfile.TemporaryDirectory() as directory:
            def archive(company, role):
                return Path(directory) / f'{company}_{role}'
            prep_dir = archive('乙', '工艺')
            prep_dir.mkdir()
            (prep_dir / 'prep.json').write_text('{}')
            with patch.object(interview.tracker_store, 'rows', return_value=applications), \
                 patch.object(interview.inbox_store, 'list_entries', return_value=candidates), \
                 patch.object(interview, '_archive', side_effect=archive):
                rows = interview.list_applications()
        self.assertEqual([(r['company'], r['role']) for r in rows],
                         [('甲', '验证'), ('乙', '工艺'), ('乙', '设备')])
        self.assertEqual([r['source'] for r in rows], ['application', 'candidate', 'candidate'])
        self.assertEqual([r['has_prep'] for r in rows], [False, True, False])
        self.assertNotIn('source', applications[0])
        self.assertNotIn('has_prep', candidates[1])

    def test_candidate_without_application_has_jd_for_preparation(self):
        candidate = {'id': '9', 'company': '芯片公司', 'role': 'IC 验证'}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(interview.tracker_store, 'rows', return_value=[]), \
             patch.object(interview.inbox_store, 'list_entries', return_value=[candidate]), \
             patch.object(interview.inbox_store, 'entry_text', return_value='验证职责和要求') as text, \
             patch.object(interview, '_archive', return_value=Path(directory)):
            self.assertEqual(interview.list_applications()[0]['source'], 'candidate')
            self.assertEqual(interview._find_jd('芯片公司', 'IC 验证'), '验证职责和要求')
            text.assert_called_once_with('9')


if __name__ == '__main__':
    unittest.main()
