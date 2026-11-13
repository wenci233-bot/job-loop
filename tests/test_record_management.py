from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.storage import inbox, tracker
from server.api import apply
from server.api.inbox import router as inbox_router
from server.api.rank import router as rank_router

class RecordManagementTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root = Path(tmp.name)
        for module, key, value in [(inbox,'INBOX_DIR',self.root/'inbox'),(inbox,'INBOX_INDEX_JSON',self.root/'index.json'),(inbox,'ensure_dirs',lambda:None),(tracker,'TRACKER_CSV',self.root/'tracker.csv'),(tracker,'ensure_dirs',lambda:None),(apply,'APPLICATIONS_DIR',self.root/'applications')]:
            p=patch.object(module,key,value);p.start();self.addCleanup(p.stop)
        app=FastAPI();app.include_router(inbox_router);app.include_router(apply.router);app.include_router(rank_router)
        self.client=TestClient(app);self.addCleanup(self.client.close)

    def add_job(self, company='公司', role='开发'):
        response=self.client.post('/inbox/save',json={'company':company,'role':role,'text':'负责 Python 开发，要求熟悉 SQL，具备项目经验。','parsed':{'salary':'20-30k'}})
        self.assertEqual(response.status_code,200,response.text);return response.json()

    def test_delete_application_restores_candidate_and_can_recreate(self):
        e=self.add_job();inbox.update_entry(e['id'],score=88,status='已评估',rank={'suggestion':'保留评分'})
        created=self.client.post('/apply/create',json={'inbox_id':e['id']}).json()['tracker_row']
        archive=self.root/'applications/公司_开发/job_posting.md';self.assertTrue(archive.exists())
        self.assertEqual(self.client.post('/apply/delete',json={'ids':[created['id']]}).status_code,422)
        result=self.client.post('/apply/delete',json={'ids':[created['id']], 'confirmed':True})
        self.assertEqual(result.json()['deleted'],1)
        self.assertTrue(archive.exists());self.assertEqual(inbox.get_entry(e['id'])['status'],'已评估')
        self.assertEqual(inbox.get_entry(e['id'])['score'],88)
        self.assertEqual(self.client.post('/apply/create',json={'inbox_id':e['id']}).status_code,200)
        self.assertEqual(len(tracker.rows()),1)

    def test_delete_candidate_preserves_application_and_other_jobs(self):
        e=self.add_job();other=self.add_job('其他公司')
        self.client.post('/apply/create',json={'inbox_id':e['id']})
        self.assertEqual(self.client.post('/inbox/delete',json={'ids':[e['id']]}).status_code,422)
        self.assertEqual(self.client.post('/inbox/delete',json={'ids':[e['id']], 'confirmed':True}).json()['deleted'],1)
        self.assertIsNone(inbox.get_entry(e['id']));self.assertIsNotNone(inbox.get_entry(other['id']))
        self.assertEqual(len(tracker.rows()),1)
        self.assertFalse((self.root/'inbox'/e['file']).exists())
        new=self.add_job()
        candidates=self.client.get('/rank/candidates').json()['entries']
        self.assertEqual(next(e for e in candidates if e['id']==new['id'])['status'],'已申请')

    def test_manual_add_dedupe_bulk_delete_and_validation(self):
        e=self.add_job()
        body={'company':'公司','role':'开发','status':'interview_1','notes':'下周面试'}
        first=self.client.post('/apply/manual',json=body).json()
        self.assertFalse(first['duplicate']);self.assertEqual(inbox.get_entry(e['id'])['status'],'已申请')
        self.assertTrue(self.client.post('/apply/manual',json=body).json()['duplicate'])
        second=self.client.post('/apply/manual',json={**body,'company':'另一家公司'}).json()['tracker_row']
        self.assertTrue(first['tracker_row']['date'])
        self.assertEqual(self.client.post('/apply/manual',json={**body,'company':' '}).status_code,422)
        self.assertEqual(self.client.post('/apply/manual',json={**body,'status':'invalid'}).status_code,400)
        ids=[first['tracker_row']['id'],second['id']]
        self.assertEqual(self.client.post('/apply/delete',json={'ids':ids,'confirmed':True}).json()['deleted'],2)
        self.assertEqual(tracker.rows(),[])

    def test_legacy_rows_get_persistent_unique_ids_without_losing_fields(self):
        tracker.TRACKER_CSV.write_text('date,company,role,status,notes\n2026-11-01,公司,开发,applied,旧备注\n2026-11-01,公司,开发,applied,另一条\n',encoding='utf-8-sig')
        rows=tracker.rows();self.assertNotEqual(rows[0]['id'],rows[1]['id'])
        self.assertEqual([r['id'] for r in tracker.rows()],[r['id'] for r in rows])
        tracker.delete_rows([rows[1]['id']])
        self.assertEqual(tracker.rows()[0]['notes'],'旧备注')
