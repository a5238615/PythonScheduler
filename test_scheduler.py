import datetime
import importlib.util
import os
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
BACKEND = os.path.join(ROOT, 'deb', 'var', 'jb', 'usr', 'libexec', 'python-scheduler.py')

spec = importlib.util.spec_from_file_location('python_scheduler_backend', BACKEND)
backend = importlib.util.module_from_spec(spec)
# Keep test-created state isolated from any real user data.
tmp = tempfile.TemporaryDirectory(prefix='pythonscheduler-test-')
os.environ['PYTHONSCHEDULER_ROOT'] = tmp.name
spec.loader.exec_module(backend)


class SchedulerDueTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.datetime(2026, 11, 17, 10, 30).astimezone()
        self.epoch = self.now.timestamp()

    def test_daily_catches_up_after_configured_time(self):
        task = {'enabled': True, 'mode': 'daily', 'time': '09:00', 'last_run': ''}
        self.assertTrue(backend.is_due(task, self.now, self.epoch))

    def test_daily_does_not_repeat_same_day(self):
        task = {'enabled': True, 'mode': 'daily', 'time': '09:00', 'last_run': '2026-11-17'}
        self.assertFalse(backend.is_due(task, self.now, self.epoch))

    def test_weekly_respects_selected_day(self):
        task = {'enabled': True, 'mode': 'weekly', 'time': '09:00', 'days': ['tue'], 'last_run': ''}
        self.assertTrue(backend.is_due(task, self.now, self.epoch))
        task['days'] = ['wed']
        self.assertFalse(backend.is_due(task, self.now, self.epoch))

    def test_interval_uses_creation_epoch(self):
        task = {'enabled': True, 'mode': 'interval', 'minutes': 10,
                'created_epoch': self.epoch - 601, 'last_epoch': 0}
        self.assertTrue(backend.is_due(task, self.now, self.epoch))

    def test_once_only_runs_on_selected_date_after_time(self):
        task = {'enabled': True, 'mode': 'once', 'date': '2026-11-17',
                'time': '10:00', 'last_run': ''}
        self.assertTrue(backend.is_due(task, self.now, self.epoch))
        task['last_run'] = '2026-11-17'
        self.assertFalse(backend.is_due(task, self.now, self.epoch))

    def test_disabled_task_never_runs(self):
        task = {'enabled': False, 'mode': 'daily', 'time': '00:00', 'last_run': ''}
        self.assertFalse(backend.is_due(task, self.now, self.epoch))


if __name__ == '__main__':
    unittest.main()
