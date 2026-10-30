import base64
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_injection as injection
from paos_contact import derive_attach, runtime_contact, save_native_targets


class OpenCodeV2Tests(unittest.TestCase):
    message_id = 'msg_' + 'a' * 32

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        auth = self.root / 'auth.json'
        auth.write_text(json.dumps({'password': 'private-fixture-凭据'}), encoding='utf-8')
        self.target = {'runtime': 'opencode', 'api_version': 2, 'session_id': 'ses_original',
                       'base_url': 'http://127.0.0.1:4135', 'auth_file': str(auth)}
        self.session = {'data': {'id': 'ses_original', 'location': {'directory': 'C:/工作区'}}}
        self.item = {'data': {'id': self.message_id, 'sessionID': 'ses_original',
                              'type': 'user', 'delivery': 'steer'}}
        for p in (patch.object(Path, 'home', return_value=self.root),
                  patch.object(injection.uuid, 'uuid4', return_value=uuid.UUID(hex='a' * 32))):
            p.start()
            self.addCleanup(p.stop)

    def request(self, state=None, last=None):
        return patch.object(injection, '_request', side_effect=[
            (self.session, 200), ({'data': state or {}}, 200),
            last if last is not None else (self.item, 200)])

    def test_idle_and_running_admit_one_text_with_session_model_unchanged(self):
        for active in ({}, {'ses_original': {'type': 'running'}}):
            with self.subTest(active=active), self.request(active) as request:
                result = injection.inject(self.target, '读原信\n中文 🐾')
            self.assertTrue(result['accepted'])
            self.assertEqual(result['message_id'], self.message_id)
            self.assertEqual(result['native_state'], 'running' if active else 'idle')
            self.assertEqual([c.args[3] for c in request.call_args_list],
                             ['/api/session/ses_original', '/api/session/active', '/api/session/ses_original/prompt'])
            self.assertEqual(request.call_args.args[4], {'id': self.message_id, 'text': '读原信\n中文 🐾'})
            expected = 'Basic ' + base64.b64encode('opencode:private-fixture-凭据'.encode()).decode()
            self.assertTrue(all(c.kwargs['authorization'] == expected for c in request.call_args_list))
            self.assertNotIn('private-fixture', json.dumps(result))
            self.assertNotIn('completed', result)

    def test_wrong_session_or_missing_location_never_posts(self):
        for session in ({'id': 'another', 'location': {'directory': 'C:/work'}},
                        {'id': 'ses_original'}, {'id': 'ses_original', 'location': {'directory': ''}}):
            self.session = {'data': session}
            with self.subTest(session=session), self.request() as request:
                with self.assertRaises(injection.InjectionError):
                    injection.inject(self.target, 'fixture')
            self.assertEqual(request.call_count, 1)

    def test_bad_state_does_not_become_idle(self):
        with patch.object(injection, '_request', side_effect=[(self.session, 200), ({}, 200)]) as request:
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, 'fixture')
        self.assertEqual(request.call_count, 2)
        with self.request({'ses_original': {'type': 'unknown'}}) as request:
            with self.assertRaises(injection.InjectionError):
                injection.inject(self.target, 'fixture')
        self.assertEqual(request.call_count, 2)

    def test_explicit_model_and_unknown_version_reject_without_native_access(self):
        with patch.object(injection, '_request') as request:
            with self.assertRaisesRegex(ValueError, 'inherit'):
                injection.inject(self.target, 'fixture', model={'providerID': 'fixture', 'modelID': 'fixture'})
            self.target['api_version'] = 3
            with self.assertRaisesRegex(ValueError, 'api_version'):
                injection.inject(self.target, 'fixture')
        request.assert_not_called()

    def test_stop_rechecked_after_readonly_preflight(self):
        stop = self.root / 'STOP'
        self.target['stop_file'] = str(stop)
        calls = 0
        def respond(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return self.session, 200
            stop.touch()
            return {'data': {}}, 200
        with patch.object(injection, '_request', side_effect=respond):
            with self.assertRaisesRegex(injection.InjectionError, 'STOP'):
                injection.inject(self.target, 'fixture')
        self.assertEqual(calls, 2)

    def test_http_rejection_or_uncertainty_never_changes_api_or_retries(self):
        for status in (400, 401, 403, 404, 409, 500, 502):
            error = HTTPError('http://127.0.0.1:4135/api/prompt', status, 'fixture', {}, None)
            expected = injection.InjectionError if status < 409 else injection.InjectionUncertain
            with self.subTest(status=status), self.request(last=error) as request:
                with self.assertRaises(expected) as raised:
                    injection.inject(self.target, 'fixture')
            self.assertEqual(isinstance(raised.exception, injection.InjectionUncertain), status >= 409)
            self.assertFalse(raised.exception.details()['retry'])
            self.assertEqual(request.call_count, 3)

    def test_lost_or_wrong_receipt_is_unknown_after_exactly_one_post(self):
        for last in (TimeoutError('fixture'), URLError('fixture'),
                     json.JSONDecodeError('fixture', '', 0), (None, 204),
                     ({'data': {**self.item['data'], 'sessionID': 'another'}}, 200),
                     ({'data': {**self.item['data'], 'id': 'msg_other'}}, 200)):
            with self.subTest(last=type(last).__name__), self.request(last=last) as request:
                with self.assertRaises(injection.InjectionUncertain) as raised:
                    injection.inject(self.target, 'fixture')
            self.assertEqual(request.call_count, 3)
            self.assertEqual(raised.exception.diagnostic['request_id'], 'a' * 32)

    def test_preflight_auth_failure_never_posts(self):
        with patch.object(injection, '_request', side_effect=HTTPError('fixture', 401, 'fixture', {}, None)) as request:
            with self.assertRaises(injection.InjectionError) as raised:
                injection.inject(self.target, 'fixture')
        self.assertNotIsInstance(raised.exception, injection.InjectionUncertain)
        self.assertEqual(raised.exception.diagnostic['http_status'], 401)
        request.assert_called_once()

    def test_preflight_connection_refused_is_offline_without_any_post(self):
        errors = (ConnectionRefusedError(10061, 'Windows fixture'),
                  URLError(ConnectionRefusedError(errno.ECONNREFUSED, 'fixture')),
                  URLError(OSError(errno.ECONNREFUSED, 'fixture')))
        for error in errors:
            for position in (1, 2):
                responses = [error] if position == 1 else [(self.session, 200), error]
                with self.subTest(error=type(error).__name__, position=position), \
                        patch.object(injection, '_request', side_effect=responses) as request:
                    with self.assertRaises(injection.InjectionError) as raised:
                        injection.inject(self.target, 'fixture')
                self.assertNotIsInstance(raised.exception, injection.InjectionUncertain)
                self.assertEqual(raised.exception.code, 'receiver_connection_refused')
                self.assertEqual(raised.exception.state, 'receiver_offline')
                self.assertEqual(raised.exception.diagnostic['phase'], 'status_read')
                self.assertFalse(raised.exception.details()['retry'])
                self.assertEqual(request.call_count, position)
                self.assertTrue(all(c.args[2] == 'GET' for c in request.call_args_list))

    def test_post_connection_refused_is_offline_but_reset_is_unknown(self):
        for error, uncertain in ((ConnectionRefusedError(errno.ECONNREFUSED, 'fixture'), False),
                                 (ConnectionResetError('fixture'), True)):
            with self.subTest(error=type(error).__name__), self.request(last=URLError(error)) as request:
                with self.assertRaises(injection.InjectionError) as raised:
                    injection.inject(self.target, 'fixture')
            self.assertEqual(isinstance(raised.exception, injection.InjectionUncertain), uncertain)
            self.assertFalse(raised.exception.details()['retry'])
            self.assertEqual(request.call_count, 3)

    def test_v2_windows_handoff_sends_only_locators_before_any_local_http(self):
        self.target.update(auth_file='C:/private/opencode-auth.json', timeout_seconds=7,
                           extension={'execution_environment': 'windows', 'windows_python': 'C:/Python/python.exe',
                                      'caller_token': 'do-not-copy'}, caller_pipe='do-not-copy')
        receipt = {'accepted': True, 'runtime': 'opencode', 'session_id': 'ses_original',
                   'message_id': self.message_id, 'api_version': 2}
        installation_path = self.root / 'fixture.json'
        with patch.object(injection.os, 'name', 'posix'), \
                patch.object(injection, '_check_stop'), \
                patch.object(injection, 'load_installation_descriptor', return_value={'configured': True, 'source_root': 'C:/PAOS'}), \
                patch.object(injection, 'resolve_installation_path', return_value=installation_path), \
                patch.object(injection.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(receipt).encode(), b'')) as run, \
                patch.object(injection, '_request') as request:
            result = injection.inject(self.target, '中文 fixture')
        run.assert_called_once()
        request.assert_not_called()
        wire = run.call_args.kwargs['input'].decode()
        self.assertNotIn('do-not-copy', wire)
        self.assertNotIn('private-fixture', wire)
        child = json.loads(wire)['target']
        self.assertEqual(child['api_version'], 2)
        self.assertEqual(child['auth_file'], 'C:/private/opencode-auth.json')
        self.assertEqual(result['execution_environment'], 'windows')

    def test_contact_v2_attach_is_real_v2_cli_without_credentials(self):
        save_native_targets(self.root, {'agent-original': self.target})
        contact = runtime_contact(self.root, 'agent-original')
        self.assertEqual(contact['attach']['command'], 'opencode --server http://127.0.0.1:4135 --session ses_original')
        self.assertNotIn('private-fixture', json.dumps(contact))
        old = derive_attach({**self.target, 'api_version': 1})
        self.assertIn('opencode attach ', old['command'])


if __name__ == '__main__':
    unittest.main()
