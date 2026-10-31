"""Real locator writes: concurrency and failed publication must preserve state."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'code/personal-agent-os/scripts'
sys.path.insert(0, str(SCRIPTS))
from paos_registry import ProjectRegistry, RegistryProblem
from paos_installation import write_installation_descriptor


class MembershipTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.install = self.root/'installation.json'
        self.vault = self.root/'中文 项目'
        self.vault.mkdir()
        write_installation_descriptor(self.install, source_root=str(SCRIPTS.parent),
            data_root=str(self.root/'data'), library_roots_config=str(self.root/'libraries.json'))
        self.registry = ProjectRegistry(self.install)
        self.registry.register('3002', root_path=str(self.vault), coordinator_home_id='3002-s001')
        self.path = self.root/'data/project-registry/projects/3002.json'
        self.before = self.path.read_bytes()
        self.fp = hashlib.sha256(self.before).hexdigest()

    def test_concurrent_same_snapshot_has_one_winner_and_no_lost_member(self):
        def add(member):
            try:
                return self.registry.add_home('3002',member,expected_fingerprint=self.fp)
            except RegistryProblem as problem:
                return problem.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(add, ['3002-s002','3002-s003']))
        winners = [r for r in results if isinstance(r,dict)]
        self.assertEqual(len(winners),1)
        self.assertIn('project_fingerprint_conflict',results)
        self.assertEqual(self.registry.read_record('3002'),winners[0]['record'])
        self.assertEqual(Path(winners[0]['backup']).read_bytes(),self.before)
        self.assertEqual(len(winners[0]['record']['homes']),2)

    def test_failed_atomic_replace_leaves_original_and_releases_lock(self):
        with patch('paos_registry.os.replace',side_effect=OSError('fixture publish failure')):
            with self.assertRaises(RegistryProblem) as caught:
                self.registry.add_home('3002','3002-s002',expected_fingerprint=self.fp)
        self.assertEqual(caught.exception.code,'project_registry_write_failed')
        self.assertEqual(self.path.read_bytes(),self.before)
        self.assertFalse(list(self.path.parent.glob('.*.members*')))
        result=self.registry.add_home('3002','3002-s002',expected_fingerprint=self.fp)
        self.assertTrue(result['added'])

    def test_legacy_record_is_not_migrated_or_overwritten(self):
        legacy=json.dumps({'schema':'paos-project/v3','id':'3002','human':{'keep':'原件'}}).encode()
        self.path.write_bytes(legacy)
        with self.assertRaises(RegistryProblem) as caught:
            self.registry.add_home('3002','3002-s002',expected_fingerprint=hashlib.sha256(legacy).hexdigest())
        self.assertEqual(caught.exception.code,'project_schema_invalid')
        self.assertEqual(self.path.read_bytes(),legacy)


if __name__ == '__main__':
    unittest.main()
