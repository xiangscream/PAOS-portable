"""Offline v3 migration: prove exact identities, task references and no source mutation."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "code/personal-agent-os/scripts"))
import convert_todo_v3 as migrator  # noqa: E402
from paos_todo import parse_todo  # noqa: E402


ALL_CURRENT = dict(
    objective='整理对话、日会与 Tips', approved_scope='只针对已授权的 OB 目录', stage='doing',
    next_action='读回今天的会议原件', waiting='等 owner 实读音频', results='已归档一场会议',
    result_refs=['[[Works/会议决策]]'], context_refs=['[[INDEX]]', '[[Materials/对话原文]]'],
    legacy_source_ref='message:human-001', inflight='录音转写待完成',
    alignment_ref='[[项目最新口径]]', input_version='Human 原话 2026-10-30',
    delivery='待 Coordinator 回告', dependencies='需要会议原录音',
    continuation_to='3002-s010', boundaries='未经确认不推广结论',
    history_ref='[[Archive/旧记录]]', latest_readback='今天 10:20 实读',
    updated_at='2026-10-30T06:00:00Z',
)
TASKS = [
    dict(id='T-001', title='完成日会整理', state='doing', waiting='',
         result='原始数据已读', artifact_ref='[[Works/会议信息]]',
         notify_after=[dict(to='3002-s010',when='已完成并回读',source_ref='mail-001')],
         source_refs=['[[Materials/日会转写]]', '录音 12:30'],
         acceptance_refs=['[[Decisions/采用记录]]']),
    dict(id='T-002', title='等待结果', state='waiting', waiting='待复核', result='',
         artifact_ref='', notify_after=[], source_refs=[], acceptance_refs=[]),
    dict(id='T-003', title='不再推进', state='cancelled', waiting='', result='Human 已撤销',
         artifact_ref='', notify_after=[], source_refs=[], acceptance_refs=[]),
]


def old_v3(kind='project_agent', *, current=None, tasks=None, eol='\n', ident=None):
    ident = ident or ('rooter-001' if kind == 'rooter' else '3002-s010')
    pid = '' if kind == 'rooter' else '3002'
    def line(k,v): return f'{k}: {json.dumps(v, ensure_ascii=False)}'
    lines = ['---',line('schema','paos-todo/v3'),line('home_kind',kind),
             line('home_id',ident),line('project_id',pid),'---','', '# Current','']
    c = dict(ALL_CURRENT if current is None else current)
    lines += [line(k,v) for k,v in c.items()]
    lines += ['','# Tasks','']
    items = TASKS if tasks is None else tasks
    if not items: lines.append('_none_')
    for task in items:
        lines += ['### '+task['id'],line('schema','paos-todo-task/v1')]
        lines += [line(k,v) for k,v in task.items() if k != 'id']
        lines.append('')
    return (eol.join(lines).rstrip()+eol).encode('utf-8')


class OfflineMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'Rooter'/'TODO.md';self.source.parent.mkdir(parents=True)
        self.output=self.root/'review'/'TODO.v4.candidate.md'

    def seed(self, text=None):
        self.source.write_bytes(old_v3() if text is None else text)
        return self.source.read_bytes()

    def test_plan_is_read_only_even_with_crlf(self):
        raw=self.seed(old_v3(eol='\r\n'))
        report=migrator.execute(self.source,self.output)
        self.assertEqual(report['mode'],'plan_only')
        self.assertEqual(self.source.read_bytes(),raw)
        self.assertFalse(self.output.parent.exists())
        self.assertEqual(report['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(report['tasks'],3)
        self.assertIn('approved_scope',report['retained_extra_fields'])

    def test_rooter_and_project_coordinator_roundtrip_with_receipts(self):
        for kind in ('rooter','project_agent'):
            with self.subTest(kind=kind):
                old=old_v3(kind)
                self.source.write_bytes(old)
                report=migrator.execute(self.source,self.output,write=True,
                          expect_home_id='rooter-001' if kind=='rooter' else '3002-s010',
                          expected_hash=hashlib.sha256(old).hexdigest())
                self.assertTrue(self.output.is_file())
                current=parse_todo(self.output.read_text(encoding='utf-8'))
                self.assertEqual(current['schema'],'paos-todo/v4')
                self.assertEqual(current['home_kind'],kind)
                self.assertEqual(current['project_id'],'' if kind=='rooter' else '3002')
                self.assertEqual(current['current']['context_refs'],ALL_CURRENT['context_refs'])
                self.assertEqual(current['current']['result_refs'],ALL_CURRENT['result_refs'])
                self.assertEqual(current['tasks'][0]['notify_after'],TASKS[0]['notify_after'])
                self.assertEqual(current['tasks'][0]['source_refs'],TASKS[0]['source_refs'])
                self.assertEqual(current['tasks'][0]['acceptance_refs'],TASKS[0]['acceptance_refs'])
                self.assertEqual([t['state'] for t in current['tasks']],['doing','waiting','cancelled'])
                self.assertIn('**approved_scope:**',current['pinned'])
                self.assertIn('**history_ref:**',current['pinned'])
                self.assertEqual(self.source.read_bytes(),old)
                self.assertEqual(report['candidate_sha256'],hashlib.sha256(self.output.read_bytes()).hexdigest())
                self.output.unlink()

    def test_no_tasks_still_valid_and_do_not_create_fake_tasks(self):
        current={'objective':'继续已有责任','next_action':'读取新输入'}
        raw=self.seed(old_v3(current=current,tasks=[]))
        migrator.execute(self.source,self.output,write=True)
        converted=parse_todo(self.output.read_text(encoding='utf-8'))
        self.assertEqual(converted['tasks'],[])
        self.assertEqual(converted['pinned'],'')
        self.assertEqual(self.source.read_bytes(),raw)

    def test_existing_candidate_is_not_overwritten(self):
        raw=self.seed();self.output.parent.mkdir()
        self.output.write_bytes(b'pre-existing owner content')
        with self.assertRaisesRegex(migrator.ConversionError,'拒绝覆盖'):
            migrator.execute(self.source,self.output,write=True)
        self.assertEqual(self.output.read_bytes(),b'pre-existing owner content')
        self.assertEqual(self.source.read_bytes(),raw)

    def test_source_and_output_must_differ(self):
        raw=self.seed()
        with self.assertRaises(migrator.ConversionError):
            migrator.execute(self.source,self.source,write=True)
        self.assertEqual(self.source.read_bytes(),raw)

    def test_expected_source_hash_blocks_stale_conversion(self):
        raw=self.seed()
        with self.assertRaisesRegex(migrator.ConversionError,'SHA-256'):
            migrator.execute(self.source,self.output,write=True,expected_hash='0'*64)
        self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),raw)

    def test_wrong_home_id_blocks_copy(self):
        raw=self.seed()
        with self.assertRaisesRegex(migrator.ConversionError,'工位身份不匹配'):
            migrator.execute(self.source,self.output,write=True,expect_home_id='3002-s099')
        self.assertFalse(self.output.exists());self.assertEqual(self.source.read_bytes(),raw)

    def test_old_v3_reader_ignored_extra_text_but_converter_rejects(self):
        source=old_v3().replace(b'# Tasks',b'Hand-written note with no key\n# Tasks')
        self.seed(source)
        with self.assertRaisesRegex(migrator.ConversionError,'第 '):
            migrator.execute(self.source,self.output,write=True)
        self.assertEqual(self.source.read_bytes(),source);self.assertFalse(self.output.exists())

    def test_unknown_current_and_task_fields_cannot_disappear(self):
        tests=[old_v3().replace(b'# Tasks',b'unknown_field: "must stay"\n# Tasks'),
               old_v3().replace(b'title: "',b'extra_field: "do not drop"\ntitle: "',1)]
        for b in tests:
            with self.subTest(case=b[:45]):
                self.seed(b)
                with self.assertRaisesRegex(migrator.ConversionError,'未知'):
                    migrator.execute(self.source,self.output,write=True)
                self.assertFalse(self.output.exists())

    def test_bad_schema_and_state_and_duplicate_id_fail(self):
        bad_schema=old_v3().replace(b'paos-todo/v3',b'paos-todo/v4',1)
        state=old_v3().replace(b'state: "doing"',b'state: "pending"',1)
        dup=old_v3(tasks=[TASKS[0],TASKS[0]])
        for case in (bad_schema,state,dup):
            with self.subTest(case=case[:60]):
                self.seed(case)
                with self.assertRaises(migrator.ConversionError):
                    migrator.execute(self.source,self.output,write=True)
                self.assertFalse(self.output.exists())

    def test_whitespace_that_would_be_lost_is_rejected(self):
        c=dict(ALL_CURRENT,next_action='  needs preserving spaces  ')
        raw=self.seed(old_v3(current=c))
        with self.assertRaisesRegex(migrator.ConversionError,'不完全一致'):
            migrator.execute(self.source,self.output,write=True)
        self.assertEqual(self.source.read_bytes(),raw)

    def test_cli_reports_hashes_without_printing_business_body(self):
        raw=self.seed()
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=migrator.main(['--source',str(self.source),'--output',str(self.output)])
        self.assertEqual(rc,0,err.getvalue())
        value=json.loads(out.getvalue())
        self.assertEqual(value['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertNotIn('录音',out.getvalue())
        self.assertFalse(self.output.exists())


if __name__=='__main__':unittest.main()
