"""Real v4 TODO Markdown parser/writer contracts with isolated on-disk files."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'code/personal-agent-os/scripts'
sys.path.insert(0, str(SCRIPTS))
from paos_todo import (TodoProblem, parse_todo, render_todo, write_todo,
                       update_todo_current, fingerprint_todo)


class TodoV4Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / '中文 work' / 'TODO.md'
        self.path.parent.mkdir()
        self.pinned = '- 当前批准方向：直接用 [[项目最新口径]]。\n\n## 原始要求\n\n> 用户说："不要再造一份项目状态"。'
        self.task = dict(id='T-009', title='整理日会：含引号 "x" 和冒号：', state='doing',
                         waiting='', result='已读来源，仍需核对', artifact_ref='[[Works/日会整理]]',
                         source_refs=['[[Materials/日会]]', '来源：录音 12:31'],
                         acceptance_refs=['[[Decisions/接受]]'],
                         notify_after=[{'to':'3002-s010','when':'完成后','source_ref':'[[原文]]'}])
        self.source = render_todo(home_kind='project_agent',home_id='3002-s010',project_id='3002',
                                  pinned=self.pinned,objective='持续维护项目口径',next_action='核对用户原话',
                                  context_refs=['[[项目最新口径]]'],tasks=[self.task])

    def test_roundtrip_with_pinned_and_wikilinks(self):
        got=parse_todo(self.source)
        self.assertEqual(got['pinned'],self.pinned)
        self.assertEqual(got['current']['next_action'],'核对用户原话')
        self.assertEqual(got['tasks'][0]['source_refs'],self.task['source_refs'])
        self.assertEqual(got['tasks'][0]['notify_after'],self.task['notify_after'])
        self.assertEqual(got['tasks'][0]['state'],'doing')
        self.assertEqual(got['tasks'][0]['title'],self.task['title'])

    def test_all_task_states_come_from_single_checkbox(self):
        for name,marker in [('todo',' '),('doing','/'),('waiting','?'),('done','x'),('cancelled','-')]:
            with self.subTest(name=name):
                source=render_todo(home_kind='rooter',home_id='rooter-001',objective='维护系统',
                                   next_action='继续',tasks=[dict(id='T-01',title='任务',state=name)])
                self.assertIn(f'- [{marker}] **T-01** · 任务',source)
                self.assertEqual(parse_todo(source)['tasks'][0]['state'],name)
                self.assertNotIn('**State:**',source)

    def test_user_checkbox_toggle_changes_machine_state(self):
        result=parse_todo(self.source.replace('- [/] **T-009**', '- [x] **T-009**'))
        self.assertEqual(result['tasks'][0]['state'],'done')
        self.assertEqual(result['counts']['done'],1)

    def test_multiline_pinned_can_hold_unbounded_requirements(self):
        text='原始对话\n' + '包含引用 "、冒号 : 和长段落。\n'*180
        item=render_todo(home_kind='rooter',home_id='rooter-001',pinned=text,
                         objective='整理',next_action='继续')
        self.assertEqual(parse_todo(item)['pinned'],text.rstrip('\n'))

    def test_empty_pinned_and_tasks_valid(self):
        parsed=parse_todo(render_todo(home_kind='rooter',home_id='rooter-001',objective='维护',next_action='接续'))
        self.assertEqual(parsed['pinned'],'')
        self.assertEqual(parsed['tasks'],[])

    def test_reject_old_schema_without_compatibility(self):
        with self.assertRaises(TodoProblem) as cm:
            parse_todo(self.source.replace('paos-todo/v4','paos-todo/v3'))
        self.assertEqual(cm.exception.code,'todo_schema_invalid')

    def test_duplicate_task_id_rejected(self):
        with self.assertRaises(TodoProblem):
            parse_todo(self.source + '\n- [ ] **T-009** · 重复\n')

    def test_unrecognized_current_field_rejected(self):
        with self.assertRaises(TodoProblem):
            parse_todo(self.source.replace('# Tasks', '- **Stage:** 虚构管理阶段\n\n# Tasks'))

    def test_malformed_task_rejected(self):
        with self.assertRaises(TodoProblem):
            parse_todo(self.source.replace('**T-009** · ', '**T-009** '))

    def test_duplicate_frontmatter_field_rejected(self):
        with self.assertRaises(TodoProblem):
            parse_todo(self.source.replace('home_id:', 'home_id: "3002-s002"\nhome_id:',1))

    def test_rooter_cannot_be_bound_to_project(self):
        with self.assertRaises(TodoProblem):
            render_todo(home_kind='rooter',home_id='rooter-001',project_id='3002',objective='维护',next_action='继续')

    def test_update_preserves_pinned_and_tasks_byte_exactly(self):
        original=self.source.replace('\n','\r\n').encode('utf-8')
        self.path.write_bytes(original)
        fp=fingerprint_todo(self.path)
        result=update_todo_current(self.path, {'next_action':'实读新的日会 "原文"'}, expected_fingerprint=fp,
                                   now='2026-10-30T08:00:00Z')
        self.assertTrue(result['changed'])
        new_bytes=self.path.read_bytes()
        before=original.split(b'# Current\r\n',1)[0]
        after=original.split(b'# Tasks\r\n',1)[1]
        self.assertTrue(new_bytes.startswith(before+b'# Current\r\n'))
        self.assertTrue(new_bytes.endswith(b'# Tasks\r\n'+after))
        self.assertNotIn(b'\n',new_bytes.replace(b'\r\n',b''))
        parsed=parse_todo(new_bytes.decode('utf-8'))
        self.assertEqual(parsed['current']['next_action'],'实读新的日会 "原文"')
        self.assertEqual(parsed['current']['updated_at'],'2026-10-30T08:00:00Z')

    def test_same_current_does_not_rewrite_or_touch_timestamp(self):
        write_todo(self.path,self.source,create_only=True)
        before=self.path.read_bytes(); fp=fingerprint_todo(self.path)
        result=update_todo_current(self.path,{'next_action':'核对用户原话'},expected_fingerprint=fp)
        self.assertFalse(result['changed'])
        self.assertEqual(self.path.read_bytes(),before)

    def test_stale_fingerprint_does_not_write(self):
        write_todo(self.path,self.source,create_only=True)
        before=self.path.read_bytes()
        with self.assertRaises(TodoProblem) as cm:
            update_todo_current(self.path,{'next_action':'覆盖'},expected_fingerprint='0'*64)
        self.assertEqual(cm.exception.code,'todo_fingerprint_conflict')
        self.assertEqual(self.path.read_bytes(),before)

    def test_full_write_guard_and_byte_preservation(self):
        write_todo(self.path,self.source,create_only=True)
        before=self.path.read_bytes()
        with self.assertRaises(TodoProblem):
            write_todo(self.path,self.source.replace('核对用户原话','覆盖'),expected_fingerprint='0'*64)
        self.assertEqual(self.path.read_bytes(),before)
        copy=self.source.replace('\n','\r\n')
        write_todo(self.path,copy,expected_fingerprint=fingerprint_todo(self.path))
        self.assertEqual(self.path.read_bytes(),copy.encode('utf-8'))

    def test_bad_full_write_never_publishes(self):
        write_todo(self.path,self.source,create_only=True)
        before=self.path.read_bytes()
        with self.assertRaises(TodoProblem):
            write_todo(self.path,self.source.replace('**Objective:**','**Wrong:**'))
        self.assertEqual(self.path.read_bytes(),before)

    def test_unknown_update_rejected_before_writing(self):
        write_todo(self.path,self.source,create_only=True)
        before=self.path.read_bytes()
        with self.assertRaises(TodoProblem):
            update_todo_current(self.path,{'stage':'过去的多余项目进度'})
        self.assertEqual(self.path.read_bytes(),before)

    def test_reject_non_string_input_no_silent_conversion(self):
        with self.assertRaises(TodoProblem):
            render_todo(home_kind='rooter',home_id='rooter-001',objective=123,next_action='继续')

if __name__=='__main__': unittest.main()
