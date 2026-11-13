import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server import config
from server.services import debrief, interview
from server.api.debrief import router

class MockImportTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        for module,key,value in [(config,'APPLICATIONS_DIR',self.root),(interview,'APPLICATIONS_DIR',self.root),(debrief,'APPLICATIONS_DIR',self.root),(interview,'ensure_dirs',lambda:None),(debrief,'ensure_dirs',lambda:None)]:
            p=patch.object(module,key,value);p.start();self.addCleanup(p.stop)
        app=FastAPI();app.include_router(router);self.client=TestClient(app);self.addCleanup(self.client.close)
        self.history=[{'role':'interviewer','text':'介绍你的项目'},{'role':'candidate','text':'原始回答'+('内容'*600)},{'role':'interviewer','text':'还有其他补充吗？'}]
        self.report={'overall':0,'per_question':[{'question':'介绍项目（模型归纳）','score':0,'verdict':'需改进','answer_summary':'回答摘要','highlights':['表达真实'],'problems':['缺少指标'],'better_answer':['补充验证结果'],'off_topic':True}],'strengths':['真实'],'weaknesses':['空泛'],'stuck_points':['项目细节'],'advice':'继续练习'}
        self.session=interview.save_mock('公司','岗位',self.history,self.report)
        self.payload={'company':'公司','role':'岗位','session_id':self.session['id']}

    def test_import_preserves_source_zero_scores_full_answers_and_analysis(self):
        source=self.root/'公司_岗位/mock_interview.json';before=source.read_bytes()
        with patch.object(debrief.ai,'chat',side_effect=AssertionError('must not call AI')):
            result=self.client.post('/debrief/import-mock',json=self.payload)
        self.assertEqual(result.status_code,200,result.text)
        entry=result.json()['round'];self.assertFalse(result.json()['duplicate'])
        self.assertEqual(entry['mock_history'],self.history);self.assertEqual(entry['mock_report'],self.report)
        self.assertEqual(len(entry['qa']),1);self.assertEqual(entry['qa'][0]['answer'],self.history[1]['text'])
        self.assertEqual(entry['review']['overall'],0);self.assertEqual(entry['review']['per_question'][0]['score'],0)
        self.assertEqual(entry['review']['per_question'][0]['improved_points'],['补充验证结果'])
        self.assertIsNone(entry['rating']);self.assertEqual(entry['source_type'],'mock_interview')
        self.assertEqual(source.read_bytes(),before)
        self.assertEqual(self.client.get('/debrief/list').json()['rounds'][0]['source_session_id'],self.session['id'])

    def test_concurrent_import_is_idempotent_and_preserves_manual_round(self):
        debrief.save_round('公司','岗位',[{'question':'正式题','answer':'正式答'}],[],3,'正式面试',None)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:debrief.import_mock('公司','岗位',self.session['id']),range(4)))
        self.assertEqual(sum(not r['duplicate'] for r in results),1)
        self.assertEqual(len(debrief.load_rounds('公司','岗位')),2)
        interview.delete_mock('公司','岗位',self.session['id'])
        self.assertTrue(debrief.import_mock('公司','岗位',self.session['id'])['duplicate'])
        self.assertEqual(len(debrief.load_rounds('公司','岗位')),2)

    def test_invalid_or_missing_source_and_corrupt_destination_do_not_overwrite(self):
        self.assertEqual(self.client.post('/debrief/import-mock',json={**self.payload,'session_id':'missing'}).status_code,404)
        self.assertEqual(self.client.post('/debrief/import-mock',json={**self.payload,'company':'其他公司'}).status_code,404)
        self.assertEqual(self.client.post('/debrief/import-mock',json={**self.payload,'company':'../outside'}).status_code,400)
        dest=self.root/'公司_岗位/debrief.json';dest.write_text('broken')
        self.assertEqual(self.client.post('/debrief/import-mock',json=self.payload).status_code,400)
        self.assertEqual(dest.read_text(),'broken')

    def test_unanswered_session_cannot_be_imported(self):
        empty=interview.save_mock('公司','岗位',[{'role':'interviewer','text':'无人回答'}],self.report)
        self.assertEqual(self.client.post('/debrief/import-mock',json={**self.payload,'session_id':empty['id']}).status_code,400)
