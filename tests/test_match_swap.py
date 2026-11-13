import json
import threading
import time
import unittest
from concurrent.futures import CancelledError
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from server.services import aimatch
from server.api import inbox


def wait_for(predicate):
    end=time.monotonic()+3
    while time.monotonic()<end:
        if predicate():return
        time.sleep(.01)
    raise AssertionError('timeout')


class MatchSwapTests(unittest.TestCase):
    def test_company_aliases_and_team_variants(self):
        for new, old in [('腾讯（混元大模型团队）','Tencent'),('字节跳动 Seed','字节跳动'),('阿里巴巴通义实验室','阿里'),('示例科技有限公司','示例科技'),('IDEA研究院','粤港澳大湾区数字经济研究院')]:
            self.assertTrue(aimatch.excluded_company(new,[old]),(new,old))
        self.assertFalse(aimatch.excluded_company('全新科技',['腾讯']))

    def test_template_filters_and_server_enforced_exclusion_with_refill(self):
        calls=[]
        outputs=[json.dumps([{'company':'腾讯（混元）','role':'改个名称'}, {'company':'新公司甲','role':'算法岗'}]),json.dumps([{'company':'新公司乙','role':'算法岗'},{'company':'新公司丙','role':'算法岗'}])]
        def chat(messages, **kwargs):
            calls.append(messages[0]['content']);return outputs[len(calls)-1]
        with patch.object(aimatch.ai,'chat',side_effect=chat):
            rows=aimatch._match_tier('冲刺',['大模型算法'],['深圳'],'日常实习',['互联网中厂'],'档案内容',['腾讯'],threading.Event())
        self.assertEqual({r['company'] for r in rows},{'新公司甲','新公司乙','新公司丙'})
        self.assertEqual(len(calls),2)
        for prompt in calls:
            for text in ['日常实习','深圳','互联网中厂','大模型算法','档案内容','冲刺','腾讯']:
                self.assertIn(text,prompt)
            self.assertNotIn('{{',prompt)

    def test_all_duplicates_never_return_as_new_results(self):
        row={'company':'腾讯','role':'算法岗','tier':'冲刺','stars':4}
        with patch.object(aimatch,'_profile_summary',return_value='档案'),patch.object(aimatch,'_match_tier',return_value=[row]):
            with self.assertRaisesRegex(RuntimeError,'不重复'):
                aimatch.match(['算法'],['深圳'],'校招',[],exclude_companies=['腾讯'])

    def test_shortage_returns_only_new_rows_and_warning(self):
        warnings=[]
        def tier(t,*args):return [{'company':'新公司'+t,'role':'算法岗','tier':t,'stars':4}]
        with patch.object(aimatch,'_profile_summary',return_value='档案'),patch.object(aimatch,'_match_tier',side_effect=tier):
            rows=aimatch.match(['算法'],[],'校招',[],warning_cb=warnings.append)
        self.assertEqual(len(rows),3);self.assertTrue(warnings)

    def test_stop_blocks_late_completion_and_is_idempotent(self):
        app=FastAPI();app.include_router(inbox.router)
        entered,release=threading.Event(),threading.Event()
        def slow(*args,**kwargs):
            entered.set();release.wait(3)
            kwargs['progress_cb']('迟到',3)
            return [{'company':'迟到公司'}]
        with TestClient(app) as client,patch.object(aimatch,'match',side_effect=slow):
            tid=client.post('/inbox/ai-match/start',json={'directions':['算法']}).json()['task_id']
            try:
                self.assertTrue(entered.wait(2))
                stop=client.post(f'/inbox/ai-match/task/{tid}/stop')
                self.assertEqual(stop.json()['status'],'cancelled')
                self.assertEqual(client.post(f'/inbox/ai-match/task/{tid}/stop').json()['status'],'cancelled')
            finally:release.set()
            wait_for(lambda:tid not in inbox._MATCH_CANCEL)
            state=client.get(f'/inbox/ai-match/task/{tid}').json()
            self.assertEqual(state['status'],'cancelled');self.assertIsNone(state['results'])
            self.assertEqual(client.post('/inbox/ai-match/task/missing/stop').status_code,404)

    def test_parallel_generation_stops_without_waiting_for_provider(self):
        entered,release,cancel=threading.Event(),threading.Event(),threading.Event()
        def slow(*args):entered.set();release.wait(3);return []
        outcome=[]
        def run():
            try:aimatch.match(['算法'],[],'校招',[],cancel_event=cancel)
            except CancelledError:outcome.append('cancelled')
        with patch.object(aimatch,'_profile_summary',return_value='档案'),patch.object(aimatch,'_match_tier',side_effect=slow):
            worker=threading.Thread(target=run);worker.start()
            try:
                self.assertTrue(entered.wait(2));cancel.set();worker.join(1)
                self.assertFalse(worker.is_alive());self.assertEqual(outcome,['cancelled'])
            finally:release.set();worker.join(3)
