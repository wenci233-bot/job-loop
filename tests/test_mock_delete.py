import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.services import interview
from server.api.interview import router

class MockDeleteTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        for key,value in [('APPLICATIONS_DIR',self.root),('ensure_dirs',lambda:None)]:
            p=patch.object(interview,key,value);p.start();self.addCleanup(p.stop)
        app=FastAPI();app.include_router(router);self.client=TestClient(app);self.addCleanup(self.client.close)
        self.history=[{'role':'interviewer','text':'问题'},{'role':'candidate','text':'回答'}]
        self.first=interview.save_mock('公司','岗位',self.history,{'overall':60})
        self.second=interview.save_mock('公司','岗位',self.history,{'overall':80})
        self.other=interview.save_mock('其他公司','岗位',self.history,{'overall':90})
        self.prep=self.root/'公司_岗位/prep.json';self.prep.write_text('{"questions":[]}')

    def delete(self, sid, **extra):
        return self.client.post('/interview/mock/delete',json={'company':'公司','role':'岗位','session_id':sid,'confirmed':True,**extra})

    def test_delete_one_preserves_other_session_and_prep(self):
        self.assertTrue(self.delete(self.first['id']).json()['deleted'])
        self.assertEqual([s['id'] for s in interview.list_mocks('公司','岗位')],[self.second['id']])
        self.assertEqual(interview.list_mocks('其他公司','岗位')[0]['id'],self.other['id'])
        self.assertEqual(self.prep.read_text(),'{"questions":[]}')
        self.assertFalse(self.delete(self.first['id']).json()['deleted'])
        self.assertTrue(self.delete(self.second['id']).json()['deleted'])
        self.assertEqual(interview.list_mocks('公司','岗位'),[])
        self.assertTrue(self.prep.exists())

    def test_confirmation_scope_and_invalid_path(self):
        self.assertEqual(self.delete(self.first['id'],confirmed=False).status_code,422)
        self.assertFalse(self.delete(self.other['id']).json()['deleted'])
        self.assertEqual(self.delete(self.first['id'],company='../outside').status_code,400)
        self.assertEqual(len(interview.list_mocks('公司','岗位')),2)

    def test_corrupt_file_not_overwritten(self):
        path=self.root/'公司_岗位/mock_interview.json';path.write_text('broken')
        self.assertEqual(self.delete(self.first['id']).status_code,400)
        self.assertEqual(path.read_text(),'broken')

    def test_concurrent_save_and_delete_preserve_new_record(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            deletion=pool.submit(interview.delete_mock,'公司','岗位',self.first['id'])
            saving=pool.submit(interview.save_mock,'公司','岗位',self.history,{'overall':95})
            self.assertTrue(deletion.result());added=saving.result()
        self.assertEqual({s['id'] for s in interview.list_mocks('公司','岗位')},{self.second['id'],added['id']})
