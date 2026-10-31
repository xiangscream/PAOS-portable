"""Real CLI + existing Home/Mail/Notice modules, disposable files, no network.

Not mocks of writers or an imported toy CLI. Only explicit native reminder
submission is stubbed: these checks must never call a paid model.
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'code' / 'personal-agent-os' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import paos
from paos_installation import write_installation_descriptor
from paos_library import ensure_workflow_library, ensure_skill_library, register_library_roots
from paos_todo import render_todo, parse_todo
from paos_registry import ProjectRegistry, RegistryProblem


class HeadlessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / '中文 工作区'
        self.root.mkdir()
        self.root = self.root.resolve()  # Windows TEMP may expose an 8.3 alias
        self.data = self.root / 'data'
        self.records = self.data / 'project-registry' / 'projects'
        self.records.mkdir(parents=True)
        self.vault = self.root / '项目库'
        self.rooter = self.root / 'Rooter' / 'rooter-001'
        self.install = self.root / 'installation.json'
        self.libconfig = self.root / 'library-roots.json'
        workflow, skill = self.root / 'workflow', self.root / 'skill'
        ensure_workflow_library(workflow)
        ensure_skill_library(skill)
        (workflow / 'Workflows' / 'intake.md').write_text('---\nschema: paos-workflow/v1\nid: daily-intake\ntitle: 每日整理\ndescription: 会议原件和最新口径\nstatus: active\n---\n# 每日整理\n', encoding='utf-8')
        self.tools = self.root / 'tools.md'
        self.tools.write_text('---\nschema: paos-tool-catalog/v1\n---\n# 本机工具\n',encoding='utf-8')
        register_library_roots(self.libconfig, workflow_root=workflow, skill_root=skill,tool_catalog=str(self.tools))
        write_installation_descriptor(self.install, source_root=str(SCRIPTS.parent), data_root=str(self.data),
                                      library_roots_config=str(self.libconfig),rooter_home=str(self.rooter),
                                      agent_numbers_config=str(self.root/'numbers.json'))
        self.project = {'schema':'paos-project-registry/v1','id':'3002',
                        'root_path':str(self.vault),'homes':['3002-s001','3002-s002'],
                        'coordinator_home_id':'3002-s001'}
        self.record = self.records / '3002.json'
        self.save_project()
        for sid in ('3002-s001','3002-s002'):
            self.make_home(self.vault / 'Workstations' / sid,sid,'3002')
        self.make_home(self.rooter,'rooter-001','')
        self.env = patch.dict(os.environ, {'HOME':str(self.root), 'USERPROFILE':str(self.root),
            'PAOS_INSTALLATION_FILE':str(self.root/'wrong-installation.json'),
            'PAOS_LIBRARY_ROOTS_CONFIG':'','PAOS_BASE_URL':'not even a URL',
            'PAOS_WORKBENCH_PROJECTION':'1','PYTHONIOENCODING':'utf-8'})
        self.env.start(); self.addCleanup(self.env.stop)
        self.net = patch('socket.create_connection',side_effect=AssertionError('network forbidden'))
        self.net.start();self.addCleanup(self.net.stop)
        self.http = patch.object(paos,'urlopen',side_effect=AssertionError('Core HTTP forbidden'))
        self.http.start();self.addCleanup(self.http.stop)

    def make_home(self,path,sid,pid):
        (path/'mailbox').mkdir(parents=True)
        (path/'notices').mkdir()
        (path/'ENTRY.md').write_text('# 入口\n参照项目最新口径。\n',encoding='utf-8')
        (path/'TODO.md').write_text(render_todo(home_kind='project_agent' if pid else 'rooter',
            home_id=sid, project_id=pid, objective='归档原件、更新已有口径',next_action='实读新增材料'),encoding='utf-8')

    def save_project(self):
        self.record.write_text(json.dumps(self.project,ensure_ascii=False),encoding='utf-8')

    def call(self,*args,ok=True):
        out,err=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            try: code=paos.main(['--installation-file',str(self.install),'--json',*args])
            except SystemExit as exc: code=exc.code
        if ok:self.assertEqual(code,0,err.getvalue()+out.getvalue())
        raw=out.getvalue() or err.getvalue()
        try:value=json.loads(raw)
        except ValueError:value=raw
        return code,value

    def send(self,mid='mail-intake-001',*extras):
        return self.call('agent','send','3002','--to','3002-s002', '--sender-kind','agent',
            '--sender-id','3002-s001','--subject','日会增量','--body','原件已保存；请更新当前口径。',
            '--message-id',mid,*extras)[1]

    def test_health_is_local_not_runtime_success(self):
        r=self.call('health')[1]
        self.assertEqual(r['backend'],'local_files')
        self.assertFalse(r['runtime_verified']);self.assertFalse(r['http_service_required'])

    def test_project_show_is_exact_registration_without_business_summary(self):
        before=self.record.read_bytes()
        r=self.call('project','show','3002')[1]
        self.assertEqual(r['project'],self.project)
        self.assertEqual(set(r['project']),{'schema','id','root_path','homes','coordinator_home_id'})
        self.assertEqual(before,self.record.read_bytes())

    def test_old_business_summary_fields_are_no_longer_in_registry_contract(self):
        for retired in ('human','generated','next_items','key_files'):
            with self.subTest(retired=retired):
                self.project[retired]='old duplicate state'
                self.save_project();before=self.record.read_bytes()
                rc,r=self.call('project','show','3002',ok=False)
                self.assertNotEqual(rc,0)
                self.assertEqual(r['error_code'],'project_schema_invalid')
                self.assertEqual(before,self.record.read_bytes())
                del self.project[retired]
                self.save_project()

    def test_orient_is_home_not_old_request_lifecycle(self):
        r=self.call('orient','3002','3002-s001')[1]
        self.assertTrue(r['todo']['trusted'])
        self.assertEqual(r['next_action'],'实读新增材料')
        self.assertNotIn('formal_requests',r['communication'])

    def test_status_does_not_probe_http(self):
        r=self.call('status','3002','3002-s001')[1]
        self.assertEqual(r['backend'],'local_files')

    def test_rooter_needs_no_project(self):
        self.record.unlink()
        r=self.call('attention','rooter-show')[1]
        self.assertEqual(r['home']['home_kind'],'rooter')

    def test_update_uses_existing_writer_and_no_projection(self):
        r=self.call('attention','todo-update','3002','3002-s001','--set','next_action=整理今日原件')[1]
        text=(self.vault/'Workstations/3002-s001/TODO.md').read_text(encoding='utf-8')
        self.assertEqual(parse_todo(text)['current']['next_action'],'整理今日原件')
        self.assertNotIn('projection',r)

    def test_pinned_and_task_checkboxes_survive_current_update(self):
        from paos_todo import render_todo, parse_todo
        path=self.vault/'Workstations/3002-s001/TODO.md'
        pinned='## 已批准方向\n\n- [[项目最新口径]] 是唯一正文。\n- Human 原话："不用仪式感管理"。'
        original=render_todo(home_kind='project_agent',home_id='3002-s001',project_id='3002',
            pinned=pinned,objective='持续整理',next_action='读新输入',
            context_refs=['[[INDEX]]'],tasks=[dict(id='T-1',title='处理日会',state='waiting',
                waiting='等转写',source_refs=['[[Materials/日会]]'])])
        path.write_text(original,encoding='utf-8')
        self.call('attention','todo-update','3002','3002-s001','--set','next_action=核对决定')
        updated=path.read_text(encoding='utf-8')
        self.assertEqual(updated.split('# Current\n')[0],original.split('# Current\n')[0])
        self.assertEqual(updated.split('# Tasks\n')[1],original.split('# Tasks\n')[1])
        parsed=parse_todo(updated)
        self.assertEqual(parsed['pinned'],pinned)
        self.assertEqual(parsed['tasks'][0]['state'],'waiting')
        self.assertEqual(parsed['current']['next_action'],'核对决定')

    def test_full_todo_write_accepts_checkbox_change_and_rejects_old_schema(self):
        from paos_todo import parse_todo, fingerprint_todo
        path=self.vault/'Workstations/3002-s001/TODO.md'
        old=path.read_text(encoding='utf-8')
        checkbox=old.replace('# Tasks\n', '# Tasks\n\n- [x] **T-004** · 归档完成\n')
        candidate=self.root/'incoming.md';candidate.write_text(checkbox,encoding='utf-8')
        fp=fingerprint_todo(path)
        self.call('attention','todo-write','3002','3002-s001','--body','@'+str(candidate),
                  '--expected-fingerprint',fp)
        self.assertEqual(parse_todo(path.read_text(encoding='utf-8'))['tasks'][0]['state'],'done')
        before=path.read_bytes()
        candidate.write_text(checkbox.replace('paos-todo/v4','paos-todo/v3'),encoding='utf-8')
        code,_=self.call('attention','todo-write','3002','3002-s001','--body','@'+str(candidate),ok=False)
        self.assertNotEqual(code,0)
        self.assertEqual(path.read_bytes(),before)

    def test_bad_fingerprint_does_not_write(self):
        path=self.vault/'Workstations/3002-s001/TODO.md';before=path.read_bytes()
        rc,_=self.call('attention','todo-update','3002','3002-s001','--set','next_action=错误覆盖',
                       '--expected-fingerprint','0'*64,ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(path.read_bytes(),before)

    def test_mail_notice_takeover_handle_loop(self):
        sent=self.send()
        self.assertFalse(sent['runtime_wake_performed'])
        self.assertEqual(self.call('inbox','3002','3002-s002')[1]['durable_mail']['unhandled_count'],1)
        files=list((self.vault/'Workstations/3002-s002/notices').glob('*.md'))
        self.assertEqual(len(files),1)
        nid=files[0].stem
        r=self.call('attention','takeover','3002','3002-s002',nid,'--set','objective=处理日会',
                    '--set','next_action=核对原件')[1]
        self.assertTrue(r['stages']['current'])
        self.assertEqual(self.call('inbox','3002','3002-s002')[1]['durable_mail']['unhandled_count'],1)
        self.call('attention','handle','3002','3002-s002',nid,'--resolution','原件已归档、口径已更新','--action-ref','Works/整理结果.md')
        self.assertEqual(self.call('inbox','3002','3002-s002')[1]['durable_mail']['unhandled_count'],0)

    def test_invalid_current_before_takeover_never_marks_notice_read(self):
        self.send('mail-takeover-invalid')
        home=self.vault/'Workstations/3002-s002'
        path=home/'TODO.md'
        before=path.read_bytes()
        notices=list((home/'notices').glob('notice-*.md'))
        self.assertEqual(len(notices),1)
        code,_=self.call('attention','takeover','3002','3002-s002',notices[0].stem,
                          '--set','next_action=',ok=False)
        self.assertNotEqual(code,0)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(list((home/'notices'/'.read').glob('*.json')))

    def test_reminder_replay_never_submits_twice(self):
        with patch.object(paos,'_remind_via_native',return_value={'agent_id':'3002-s002','state':'accepted','accepted':True}) as inject:
            self.send('mail-remind-001','--remind')
            self.send('mail-remind-001','--remind')
            self.assertEqual(inject.call_count,1)

    def test_uncertain_reminder_keeps_mail_and_no_replay(self):
        with patch.object(paos,'_remind_via_native',return_value={'agent_id':'3002-s002','state':'delivery_uncertain','accepted':None,'retry':False}) as inject:
            first=self.send('mail-unknown-001','--remind')
            self.send('mail-unknown-001','--remind')
            self.assertEqual(inject.call_count,1)
        self.assertTrue((self.vault/'Workstations/3002-s002/mailbox/mail-unknown-001.md').exists())
        self.assertIsNone(first['reminders'][0]['accepted'])

    def test_library_search_runs_on_existing_filesystem_helper(self):
        r=self.call('library','search','会议')[1]
        self.assertIn('daily-intake',json.dumps(r,ensure_ascii=False))

    def test_library_tools_raw_markdown(self):
        r=self.call('library','tools')[1]
        self.assertEqual(r['raw_markdown'],self.tools.read_text(encoding='utf-8'))

    def test_project_experience_is_ordinary_markdown(self):
        p=self.vault/'Materials'/'TIPS.md';p.parent.mkdir();p.write_text('# 经验\n一次原件，多处引用。',encoding='utf-8')
        self.assertEqual(self.call('project','experience','3002')[1]['raw_markdown'],p.read_text(encoding='utf-8'))

    def test_explicit_installation_is_scoped(self):
        before=os.environ['PAOS_INSTALLATION_FILE']
        self.call('attention','show','3002','3002-s001')
        self.assertEqual(os.environ['PAOS_INSTALLATION_FILE'],before)

    def test_unknown_project_does_not_create_files(self):
        rc,r=self.call('project','show','3003',ok=False)
        self.assertEqual(r['error_code'],'project_not_registered')
        self.assertNotEqual(rc,0);self.assertFalse((self.records/'3003.json').exists())

    def test_corrupt_registry_is_not_empty_success(self):
        self.record.write_text('{bad',encoding='utf-8')
        rc,r=self.call('project','show','3002',ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(r['error_code'],'project_registry_unreadable')

    def test_duplicate_member_is_rejected(self):
        self.project['homes'].append(self.project['homes'][0]);self.save_project()
        self.assertEqual(self.call('project','show','3002',ok=False)[1]['error_code'],'project_members_invalid')

    def test_unknown_home_is_not_guessed(self):
        rc,r=self.call('orient','3002','3002-s099',ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(r['error_code'],'home_agent_unknown')

    def test_obsolete_commands_are_removed(self):
        for args in [('project','progress-update','3002'),('session','show','3002','3002-s001'),('workbench','build'),('tips','search','x')]:
            with self.subTest(args=args):self.assertEqual(self.call(*args,ok=False)[0],2)

    def test_real_cli_subprocess_without_server(self):
        env=dict(os.environ,PAOS_INSTALLATION_FILE=str(self.install),PAOS_BASE_URL='invalid')
        p=subprocess.run([sys.executable,str(SCRIPTS/'paos.py'),'--json','attention','show','3002','3002-s001'],env=env,cwd=self.root,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['home']['home_id'],'3002-s001')

    def test_cross_project_delivery_honors_explicit_installation(self):
        p2=dict(self.project,id='3003',root_path=str(self.root/'另一项目'),homes=['3003-s001'],coordinator_home_id='3003-s001')
        (self.records/'3003.json').write_text(json.dumps(p2),encoding='utf-8')
        target=Path(p2['root_path'])/'Workstations/3003-s001';self.make_home(target,'3003-s001','3003')
        self.call('agent','send','3002','--to','3003-s001','--subject','跨项目','--body','原件入口','--message-id','cross-test-001')
        self.assertTrue((target/'mailbox/cross-test-001.md').exists())

    def test_rooter_receives_durable_input_without_project_identity(self):
        self.call('agent','send','3002','--to','rooter-001','--subject','安装接续','--body','原件入口','--message-id','rooter-test-001')
        self.assertTrue((self.rooter/'mailbox/rooter-test-001.md').exists())

    def test_mail_reply_reaches_installation_rooter_and_is_consumable(self):
        self.call('agent','send','3002','--to','3002-s002','--sender-kind','agent',
                  '--sender-id','rooter-001','--subject','安装回告','--body','请回告',
                  '--message-id','rooter-request')
        result=self.call('mail','reply','3002','3002-s002','rooter-request',
                         '--body','真实结果入口','--message-id','rooter-reply')[1]
        self.assertEqual(result['mail']['deliveries'][0]['path'],
                         str(self.rooter/'mailbox/rooter-reply.md'))
        self.assertFalse((self.vault/'Workstations/rooter-001').exists())
        state=self.call('attention','rooter-show')[1]
        notice=next(n for n in state['notices']['items'] if n['source_ref']=='rooter-reply')
        self.call('attention','rooter-read',notice['notice_id'])
        self.call('attention','rooter-handle',notice['notice_id'],
                  '--resolution','已核结果','--action-ref','Works/验收结果.md')
        state=self.call('attention','rooter-show')[1]
        notice=next(n for n in state['notices']['items'] if n['source_ref']=='rooter-reply')
        self.assertEqual(notice['state'],'handled');self.assertTrue(notice['read'])
        original=self.call('mail','read','3002','3002-s002','rooter-request')[1]
        self.assertEqual(original['notice']['resolution'],'replied')
        self.assertEqual(original['notice']['action_ref'],'rooter-reply')

    def test_mail_reply_uses_registered_same_and_cross_project_homes(self):
        p2=dict(self.project,id='3003',root_path=str(self.root/'另一项目'),
                homes=['3003-s001'],coordinator_home_id='3003-s001')
        (self.records/'3003.json').write_text(json.dumps(p2),encoding='utf-8')
        target=Path(p2['root_path'])/'Workstations/3003-s001'
        self.make_home(target,'3003-s001','3003')
        before={p:p.read_bytes() for p in self.records.glob('*.json')}
        for sender,home in [('3002-s001',self.vault/'Workstations/3002-s001'),
                            ('3003-s001',target)]:
            with self.subTest(sender=sender):
                mid='request-'+sender;reply_id='reply-'+sender
                self.call('agent','send','3002','--to','3002-s002','--sender-kind','agent',
                          '--sender-id',sender,'--subject','回告','--body','请回复','--message-id',mid)
                self.call('mail','reply','3002','3002-s002',mid,
                          '--body','结果入口','--message-id',reply_id)
                self.assertTrue((home/'mailbox'/f'{reply_id}.md').is_file())
                reply_bytes=(home/'mailbox'/f'{reply_id}.md').read_bytes()
                self.call('mail','reply','3002','3002-s002',mid,
                          '--body','结果入口','--message-id',reply_id)
                self.assertEqual((home/'mailbox'/f'{reply_id}.md').read_bytes(),reply_bytes)
                self.assertEqual(len(list((home/'notices').glob('notice-*.md'))),1)
        self.assertEqual(before,{p:p.read_bytes() for p in self.records.glob('*.json')})
        self.assertFalse((self.vault/'Workstations/3003-s001').exists())

    def test_mail_reply_rejects_unregistered_or_non_v4_rooter_before_dispatch(self):
        for failure in ('unregistered','v3'):
            with self.subTest(failure=failure):
                mid='rooter-request-'+failure;reply_id='rooter-reply-'+failure
                self.call('agent','send','3002','--to','3002-s002','--sender-kind','agent',
                          '--sender-id','rooter-001','--subject','回告','--body','请回复',
                          '--message-id',mid)
                config=self.install.read_bytes();todo=(self.rooter/'TODO.md').read_bytes()
                if failure=='unregistered':
                    data=json.loads(config);data['rooter_home']=''
                    self.install.write_text(json.dumps(data),encoding='utf-8')
                else:
                    (self.rooter/'TODO.md').write_bytes(todo.replace(b'paos-todo/v4',b'paos-todo/v3'))
                before={str(p):p.read_bytes() for p in self.vault.rglob('*')
                        if p.is_file() and '.read' not in p.parts}
                rc,result=self.call('mail','reply','3002','3002-s002',mid,
                                    '--body','不可误报已回复','--message-id',reply_id,ok=False)
                self.assertNotEqual(rc,0)
                self.assertEqual(result['error_code'],'attention_recipient_home_not_registered'
                                 if failure=='unregistered' else 'attention_home_not_v4')
                # Reading the source may mark it read; it must stay unhandled with no reply dispatch.
                self.assertFalse((self.rooter/'mailbox'/f'{reply_id}.md').exists())
                self.assertEqual(before,{str(p):p.read_bytes() for p in self.vault.rglob('*')
                                         if p.is_file() and '.read' not in p.parts})
                self.install.write_bytes(config);(self.rooter/'TODO.md').write_bytes(todo)
                original=self.call('mail','read','3002','3002-s002',mid)[1]
                self.assertEqual(original['notice']['state'],'pending')

    def test_rooter_full_todo_write_honors_fingerprint_and_identity(self):
        from paos_todo import fingerprint_todo
        path=self.rooter/'TODO.md';fp=fingerprint_todo(path)
        old=path.read_text(encoding='utf-8')
        candidate=self.root/'rooter-candidate.md'
        text=old.replace('# Tasks\n','# Tasks\n\n- [x] **BASELINE** · 收口验收\n')
        candidate.write_text(text,encoding='utf-8')
        self.call('attention','rooter-todo-write','--body','@'+str(candidate),
                  '--expected-fingerprint',fp)
        self.assertEqual(parse_todo(path.read_text(encoding='utf-8'))['tasks'][0]['state'],'done')
        before=path.read_bytes()
        rc,result=self.call('attention','rooter-todo-write','--body','@'+str(candidate),
                            '--expected-fingerprint',fp,ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(result['error_code'],'todo_fingerprint_conflict')
        self.assertEqual(path.read_bytes(),before)
        candidate.write_text(text.replace('home_id: "rooter-001"','home_id: "rooter-wrong"'),encoding='utf-8')
        rc,_=self.call('attention','rooter-todo-write','--body','@'+str(candidate),
                       '--expected-fingerprint',fingerprint_todo(path),ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(path.read_bytes(),before)

    def test_peers_and_team_use_local_roster(self):
        for command in ('peers','team'):
            r=self.call(command,'3002','3002-s001')[1]
            self.assertIn('3002-s002',json.dumps(r))

    def test_wake_status_does_not_require_server(self):
        self.assertEqual(self.call('wake','status','3002','3002-s001')[1]['agent_id'],'3002-s001')

    def test_read_commands_do_not_change_files(self):
        def snapshot():
            return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        before=snapshot()
        for args in [('health',),('orient','3002','3002-s001'),('inbox','3002','3002-s001'),
                     ('project','show','3002'),('library','search','会议')]:self.call(*args)
        self.assertEqual(before,snapshot())

    def test_no_inherited_native_binding(self):
        # The new registration cannot carry original-machine Runtime metadata.
        self.project['runtime_session']={'session_id':'old-machine-id'}
        self.save_project()
        self.assertEqual(self.call('project','show','3002',ok=False)[1]['error_code'],'project_schema_invalid')
        del self.project['runtime_session'];self.save_project()
        rc,r=self.call('wake','bind','3002','3002-s001','--driver','codex',ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(r['error_code'],'wake_native_session_missing')

    def test_cat_is_explicit_external_transport(self):
        self.install.unlink()
        with patch.object(paos.RestClient,'request',return_value={'ok':True,'rooms':[]}) as http:
            self.call('cat','list')
            http.assert_called_once_with('GET','/api/rooms')

    def test_minimal_registered_home_can_be_initialized(self):
        self.project['homes'].append('3002-s003');self.save_project()
        config=json.loads(self.install.read_text(encoding='utf-8'));config['agent_numbers_config']=''
        self.install.write_text(json.dumps(config),encoding='utf-8')
        self.call('workstation','init','3002','3002-s003','--objective','接续实际工作')
        path=self.vault/'Workstations/3002-s003/TODO.md'
        self.assertEqual(parse_todo(path.read_text(encoding='utf-8'))['schema'],'paos-todo/v4')
        self.call('orient','3002','3002-s003')

    def test_malformed_coordinator_is_explicit_error(self):
        self.project['coordinator_home_id']=[];self.save_project()
        rc,r=self.call('project','show','3002',ok=False)
        self.assertNotEqual(rc,0);self.assertEqual(r['error_code'],'project_coordinator_invalid')


    def test_register_creates_minimal_one_home_without_any_project_report(self):
        self.record.unlink()
        out=self.call('project','register','3002','--root',str(self.vault),
                      '--coordinator','3002-s001')[1]
        self.assertTrue(out['created'])
        stored=json.loads(self.record.read_text(encoding='utf-8'))
        self.assertEqual(stored['homes'],['3002-s001'])
        self.assertEqual(set(stored),{'schema','id','root_path','homes','coordinator_home_id'})
        self.assertEqual(self.call('project','show','3002')[1]['project'],stored)

    def test_register_existing_same_bytes_is_noop_but_conflict_is_not_overwritten(self):
        before=self.record.read_bytes()
        out=self.call('project','register','3002','--root',str(self.vault),
                      '--coordinator','3002-s001','--home','3002-s002')[1]
        self.assertFalse(out['created'])
        self.assertEqual(before,self.record.read_bytes())
        rc,r=self.call('project','register','3002','--root',str(self.vault),
                      '--coordinator','3002-s002',ok=False)
        self.assertNotEqual(rc,0)
        self.assertEqual(r['error_code'],'project_already_registered')
        self.assertEqual(before,self.record.read_bytes())

    def test_add_registered_home_then_init_and_deliver_without_core(self):
        before=self.record.read_bytes()
        result=self.call('project','home-add','3002','3002-s003',
                         '--expected-fingerprint',hashlib.sha256(before).hexdigest())[1]
        self.assertTrue(result['added'])
        self.assertEqual(Path(result['backup']).read_bytes(),before)
        record=self.call('project','show','3002')[1]['project']
        self.assertEqual(set(record),set(self.project))
        self.assertEqual(record['root_path'],self.project['root_path'])
        self.assertEqual(record['coordinator_home_id'],'3002-s001')
        self.assertEqual(record['homes'],['3002-s001','3002-s002','3002-s003'])
        home=self.vault/'Workstations/3002-s003'
        self.assertFalse(home.exists())
        config=json.loads(self.install.read_text(encoding='utf-8'));config['agent_numbers_config']=''
        self.install.write_text(json.dumps(config),encoding='utf-8')
        self.call('workstation','init','3002','3002-s003')
        self.assertEqual(parse_todo((home/'TODO.md').read_text(encoding='utf-8'))['home_id'],'3002-s003')
        self.call('agent','send','3002','--to','3002-s003','--subject','新成员接续',
                  '--body','实读本人Home','--message-id','new-home-intake')
        self.assertTrue((home/'mailbox/new-home-intake.md').is_file())
        self.assertEqual(len(list((home/'notices').glob('notice-*.md'))),1)
        current=self.record.read_bytes()
        result=self.call('project','home-add','3002','3002-s003',
                         '--expected-fingerprint',hashlib.sha256(current).hexdigest())[1]
        self.assertFalse(result['added']);self.assertEqual(self.record.read_bytes(),current)

    def test_add_home_rejects_stale_fingerprint_and_cross_project_id(self):
        before=self.record.read_bytes()
        for member,fp,error in [('3002-s003','0'*64,'project_fingerprint_conflict'),
                                ('3003-s003',hashlib.sha256(before).hexdigest(),'project_members_invalid')]:
            with self.subTest(member=member):
                rc,result=self.call('project','home-add','3002',member,
                                    '--expected-fingerprint',fp,ok=False)
                self.assertNotEqual(rc,0);self.assertEqual(result['error_code'],error)
                self.assertEqual(self.record.read_bytes(),before)
        self.assertFalse((self.records/'.backups').exists())

    def test_register_refuses_missing_vault_and_does_not_make_registry(self):
        self.record.unlink()
        rc,r=self.call('project','register','3002','--root',str(self.root/'not-existing'),
                       '--coordinator','3002-s001',ok=False)
        self.assertNotEqual(rc,0)
        self.assertEqual(r['error_code'],'project_root_invalid')
        self.assertFalse(self.record.exists())

    def test_register_never_overwrites_original_v3_project_file(self):
        legacy={'schema':'paos-project/v3','id':'3002','human':{'original_requirement':'must retain'}}
        self.record.write_text(json.dumps(legacy),encoding='utf-8')
        before=self.record.read_bytes()
        rc,r=self.call('project','register','3002','--root',str(self.vault),
                       '--coordinator','3002-s001',ok=False)
        self.assertNotEqual(rc,0)
        self.assertEqual(r['error_code'],'project_schema_invalid')
        self.assertEqual(self.record.read_bytes(),before)

    def test_register_rejects_invalid_home_and_duplicate_member(self):
        self.record.unlink()
        for extra in (('3002-s002','3002-s002'),('3003-s001',),('rooter-001',)):
            with self.subTest(extra=extra):
                rc,r=self.call('project','register','3002','--root',str(self.vault),
                               '--coordinator','3002-s001',*sum((['--home',h] for h in extra),[]),ok=False)
                self.assertNotEqual(rc,0)
                self.assertEqual(r['error_code'],'project_members_invalid')
                self.assertFalse(self.record.exists())


if __name__=='__main__':unittest.main()
