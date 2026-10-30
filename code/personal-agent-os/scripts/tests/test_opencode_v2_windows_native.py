"""Opt-in Windows product test with a local provider fixture, no paid model calls."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runtime_injection as injection


@unittest.skipUnless(os.name == 'nt' and os.environ.get('PAOS_TEST_OPENCODE_V2_EXE'),
                     'Explicit Windows OpenCode v2 local-only product check')
class WindowsNativeOpenCodeV2Tests(unittest.TestCase):
    def test_authenticated_prompt_is_consumed_by_native_loop_with_inherited_fixture_model(self):
        marker = 'PAOS_V2_NATIVE_' + secrets.token_hex(8)
        observed = []

        class Provider(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                observed.append(body)
                reply = marker + ('_WSL' if marker + '_WSL' in json.dumps(body) else '')
                chunks = [
                    {'id': 'chatcmpl-fixture', 'object': 'chat.completion.chunk', 'created': 1,
                     'model': 'fixture', 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': reply}, 'finish_reason': None}]},
                    {'id': 'chatcmpl-fixture', 'object': 'chat.completion.chunk', 'created': 1,
                     'model': 'fixture', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}],
                     'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}]
                data = ''.join('data: ' + json.dumps(chunk) + '\n\n' for chunk in chunks) + 'data: [DONE]\n\n'
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(data.encode())))
                self.end_headers()
                self.wfile.write(data.encode())

        provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
        thread = threading.Thread(target=provider.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(provider.server_close)
        self.addCleanup(provider.shutdown)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / 'config/opencode/opencode.json'
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                'model': 'paos-fixture/fixture', 'enabled_providers': ['paos-fixture'], 'snapshots': False,
                'providers': {'paos-fixture': {
                    'package': '@opencode/ai/providers/openai-compatible',
                    'settings': {'baseURL': f'http://127.0.0.1:{provider.server_port}/v1', 'apiKey': 'fixture'},
                    'models': {'fixture': {'name': 'PAOS local fixture'}}}}}), encoding='utf-8')
            password = secrets.token_urlsafe(32)
            auth_file = root / 'server-auth.json'
            auth_file.write_text(json.dumps({'password': password}), encoding='utf-8')
            env = {**os.environ, 'OPENCODE_PASSWORD': password, 'OPENCODE_DB': str(root / 'check.db'),
                   'OPENCODE_CONFIG': str(config), 'OPENCODE_DISABLE_FREE_MODELS': '1'}
            for variable, name in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                                   ('XDG_STATE_HOME', 'state'), ('XDG_CACHE_HOME', 'cache')]:
                env[variable] = str(root / name)
            auth = 'Basic ' + base64.b64encode(('opencode:' + password).encode()).decode()
            opener = build_opener(ProxyHandler({}))
            origin = 'http://127.0.0.1:4135'

            def call(method, path, payload=None):
                data = None if payload is None else json.dumps(payload).encode()
                request = Request(origin + path, data=data, method=method,
                                  headers={'Authorization': auth, 'Content-Type': 'application/json'})
                with opener.open(request, timeout=10) as response:
                    return json.load(response)

            with (root / 'stdout.log').open('wb') as stdout, (root / 'stderr.log').open('wb') as stderr:
                process = subprocess.Popen([os.environ['PAOS_TEST_OPENCODE_V2_EXE'], 'serve',
                                            '--hostname', '127.0.0.1', '--port', '4135'],
                                           cwd=root, env=env, stdout=stdout, stderr=stderr,
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    for attempt in range(80):
                        self.assertIsNone(process.poll(), 'Isolated product server exited')
                        try:
                            info = call('GET', '/api/info')
                            break
                        except URLError:
                            time.sleep(.25)
                    else:
                        self.fail('Isolated authenticated server did not become ready')
                    self.assertEqual(info['version'], '2.0.32')
                    session = call('POST', '/api/session', {'location': {'directory': str(root)},
                                   'model': {'providerID': 'paos-fixture', 'id': 'fixture'}, 'title': 'PAOS disposable wake fixture'})['data']
                    target = {'runtime': 'opencode', 'api_version': 2, 'base_url': origin,
                              'session_id': session['id'], 'auth_file': str(auth_file)}
                    receipt = injection.inject(target, 'Consume this local transport test: ' + marker)
                    self.assertTrue(receipt['accepted'])
                    self.assertEqual(receipt['session_id'], session['id'])
                    transcript = None
                    for attempt in range(120):
                        transcript = call('GET', f"/api/session/{session['id']}/message")
                        if any(message.get('type') == 'assistant' and marker in json.dumps(message.get('content'))
                               and message.get('time', {}).get('completed')
                               for message in transcript.get('data', [])):
                            break
                        time.sleep(.25)
                    else:
                        self.fail('Native loop did not yield an assistant message: ' + json.dumps(transcript, ensure_ascii=False)[:1800])
                    self.assertTrue(any(marker in json.dumps(request) for request in observed))
                    current = call('GET', f"/api/session/{session['id']}")['data']
                    self.assertEqual(current['model'], session['model'])
                    print(json.dumps({'product': info['version'], 'accepted': True, 'session_id': session['id'],
                                      'message_id': receipt['message_id'], 'local_provider_requests': len(observed),
                                      'native_assistant_observed': True, 'external_model_calls': 0}))
                    if os.environ.get('PAOS_TEST_OPENCODE_V2_WSL'):
                        source = Path(__file__).resolve().parents[2]
                        installation = root / 'candidate-installation.json'
                        installation.write_text(json.dumps({'schema': 'paos-installation/v1',
                            'source_root': str(source), 'data_root': str(root),
                            'library_roots_config': str(root / 'libraries.json')}), encoding='utf-8')
                        def wslpath(path):
                            return '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]
                        target['extension'] = {'execution_environment': 'windows', 'windows_python': sys.executable}
                        child = subprocess.run(['wsl.exe', '-u', 'remo', '--', 'env',
                            'PAOS_INSTALLATION_FILE=' + wslpath(installation), 'python3',
                            wslpath(source / 'scripts/runtime_injection.py')],
                            input=json.dumps({'target': target, 'message': 'WSL native test: ' + marker + '_WSL'}).encode(),
                            capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
                        self.assertEqual(child.returncode, 0, child.stdout.decode('utf-8', errors='replace'))
                        wsl_receipt = json.loads(child.stdout.decode('utf-8-sig'))
                        self.assertEqual(wsl_receipt['execution_environment'], 'windows')
                        self.assertTrue(wsl_receipt['accepted'])
                        self.assertNotEqual(wsl_receipt['message_id'], receipt['message_id'])
                        for attempt in range(120):
                            transcript = call('GET', f"/api/session/{session['id']}/message")
                            if any(message.get('type') == 'assistant' and marker + '_WSL' in json.dumps(message.get('content'))
                                   and message.get('time', {}).get('completed')
                                   for message in transcript.get('data', [])):
                                break
                            time.sleep(.25)
                        else:
                            self.fail('WSL->Windows new input was not consumed by the native loop')
                        print(json.dumps({'caller': 'WSL', 'executor': 'Windows Python',
                            'accepted': True, 'message_id': wsl_receipt['message_id'],
                            'native_assistant_observed': True, 'external_model_calls': 0}))
                finally:
                    process.terminate()
                    process.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
