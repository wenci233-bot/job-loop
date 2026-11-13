import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.services import debrief, interview
from server.api.debrief import router as debrief_router
from server.api.interview import router as interview_router

class AutoHistoryTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        for module,key,value in [(interview,'APPLICATIONS_DIR',self.root),(debrief,'APPLICATIONS_DIR',self.root),(interview,'ensure_dirs',lambda:None),(debrief,'ensure_dirs',lambda:None)]:
            p=patch.object(module,key,value);p.start();self.addCleanup(p.stop)
        app=FastAPI();app.include_router(debrief_router);app.include_router(interview_router)
        self.client=TestClient(app);self.addCleanup(self.client.close)
        self.history=[{'role':'interviewer','text':'项目问题'},{'role':'candidate','text':'项目回答'}]
        self.report={'overall':0,'per_question':[{'question':'项目问题','score':0,'verdict':'需改进','problems':['缺少指标'],'better_answer':['补充实验']}],'advice':'练习'}

    def listing(self):return self.client.get('/debrief/list').json()['rounds']
    def delete(self,row):return self.client.post('/debrief/delete',json={'archive':row['company_role'],'id':row['id'],'confirmed':True})

    def test_old_records_auto_backfilled_and_repeated_reads_do_not_duplicate(self):
        session=interview.save_mock('旧公司','旧岗位',self.history,self.report)
        self.assertFalse((self.root/'旧公司_旧岗位/debrief.json').exists())
        for _ in range(3):
            rows=self.listing();self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['source_session_id'],session['id']);self.assertEqual(rows[0]['review']['overall'],0)
        self.assertTrue((self.root/'旧公司_旧岗位/debrief.json').exists())

    def test_new_save_automatically_persists_debrief_before_returning(self):
        result=self.client.post('/interview/mock/save',json={'company':'新公司','role':'岗位','history':self.history,'report':self.report})
        self.assertEqual(result.status_code,200,result.text);self.assertTrue(result.json()['debrief_synced'])
        self.assertEqual(len(debrief.load_rounds('新公司','岗位')),1)
        self.assertEqual(len(self.listing()),1)

    def test_deleted_mock_debrief_stays_deleted_and_other_data_survives(self):
        session=interview.save_mock('公司','岗位',self.history,self.report)
        debrief.save_round('公司','岗位',[{'question':'正式题','answer':'正式答'}],[],3,'保留',None)
        prep=self.root/'公司_岗位/prep.json';prep.write_text('{}')
        imported=next(r for r in self.listing() if r.get('source_type')=='mock_interview')
        self.assertTrue(self.delete(imported).json()['deleted'])
        for _ in range(3):
            rows=self.listing();self.assertEqual(len(rows),1);self.assertEqual(rows[0]['note'],'保留')
        self.assertEqual(interview.list_mocks('公司','岗位')[0]['id'],session['id']);self.assertTrue(prep.exists())
        self.assertTrue(self.delete(rows[0]).json()['deleted']);self.assertEqual(self.listing(),[])
        debrief.save_round('公司','岗位',[{'question':'新题','answer':'新答'}],[],3,'新复盘',None)
        self.assertEqual(len(self.listing()),1)
        self.client.post('/interview/mock/save',json={'company':'公司','role':'岗位','history':self.history,'report':self.report})
        self.assertEqual(len(self.listing()),2)

    def test_legacy_ids_and_delete_validation(self):
        path=self.root/'公司_岗位/debrief.json';path.parent.mkdir()
        path.write_text(json.dumps({'rounds':[{'round':1,'date':'2026-11-01','note':'原有数据'}]}))
        row=self.listing()[0];self.assertEqual(self.listing()[0]['id'],row['id'])
        self.assertEqual(self.client.post('/debrief/delete',json={'archive':'公司_岗位','id':row['id']}).status_code,422)
        self.assertEqual(self.client.post('/debrief/delete',json={'archive':'../outside','id':row['id'],'confirmed':True}).status_code,400)
        self.assertEqual(len(self.listing()),1)
