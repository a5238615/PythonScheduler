import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import test_scheduler as shared
backend = shared.backend

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = backend.SchedulerHTTPServer(('127.0.0.1', 0), backend.Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, method='GET', payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', data=data, method=method, headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def test_health(self):
        code, body = self.request('/health')
        self.assertEqual(code, 200)
        self.assertTrue(body['ok'])
        self.assertEqual(body['version'], '1.2.3')

    def test_create_script_and_daily_task(self):
        import base64
        code, script = self.request('/scripts', 'POST', {'name':'hello.py', 'content':base64.b64encode(b'print("ok")').decode()})
        self.assertEqual(code, 201)
        code, task = self.request('/tasks', 'POST', {'name':'daily', 'script_id':script['id'], 'mode':'daily', 'time':'09:30', 'minutes':60})
        self.assertEqual(code, 201)
        self.assertEqual(task['script_id'], script['id'])
        code, _ = self.request('/tasks/' + task['id'], 'PATCH', {'enabled':False})
        self.assertEqual(code, 200)
        code, _ = self.request('/tasks/' + task['id'], 'DELETE')
        self.assertEqual(code, 200)
        code, _ = self.request('/scripts/' + script['id'], 'DELETE')
        self.assertEqual(code, 200)

    def test_reject_invalid_weekday(self):
        import base64
        _, script = self.request('/scripts', 'POST', {'name':'x.py', 'content':base64.b64encode(b'pass').decode()})
        code, body = self.request('/tasks', 'POST', {'script_id':script['id'], 'mode':'weekly', 'time':'10:00', 'days':['noday']})
        self.assertEqual(code, 400)
        self.assertIn('weekday', body['error'])
        self.request('/scripts/' + script['id'], 'DELETE')

    def test_reject_invalid_once_date(self):
        import base64
        _, script = self.request('/scripts', 'POST', {'name':'x.py', 'content':base64.b64encode(b'pass').decode()})
        code, body = self.request('/tasks', 'POST', {'script_id':script['id'], 'mode':'once', 'time':'10:00', 'date':'not-a-date'})
        self.assertEqual(code, 400)
        self.assertIn('YYYY-MM-DD', body['error'])
        self.request('/scripts/' + script['id'], 'DELETE')

    def test_reject_pip_option_injection(self):
        import base64
        _, script = self.request('/scripts', 'POST', {'name':'x.py', 'content':base64.b64encode(b'pass').decode()})
        code, body = self.request('/pip', 'POST', {'script_id':script['id'], 'package':'--index-url=https://bad.invalid'})
        self.assertEqual(code, 400)
        self.assertIn('invalid package', body['error'])
        self.request('/scripts/' + script['id'], 'DELETE')

if __name__ == '__main__':
    unittest.main()
