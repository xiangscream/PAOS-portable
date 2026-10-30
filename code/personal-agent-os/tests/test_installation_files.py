"""Current installation contracts retained from D3.2 without the removed Core."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from paos_installation import InstallationProblem,write_installation_descriptor,load_installation_descriptor
from paos_backup import create_backup,restore_backup
from paos_registry import ProjectRegistry,RegistryProblem


class InstallationFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.install=self.root/'installation.json'
        self.source=self.root/'source';self.source.mkdir()
        self.data=self.root/'data';self.data.mkdir()
        self.lib=self.root/'library-roots.json'

    def configure(self,**kwargs):
        return write_installation_descriptor(self.install,source_root=str(self.source),
            library_roots_config=str(self.lib),**kwargs)

    def test_new_install_requires_data_root(self):
        with self.assertRaises(InstallationProblem) as e:self.configure()
        self.assertEqual(e.exception.code,'installation_data_root_missing')
        self.assertFalse(self.install.exists())

    def test_source_change_preserves_data_and_home(self):
        self.configure(data_root=str(self.data),rooter_home=str(self.root/'rooter'))
        self.source=self.root/'sourceB';self.configure()
        value=load_installation_descriptor(self.install)
        self.assertEqual(Path(value['data_root']),self.data)
        self.assertEqual(Path(value['rooter_home']),self.root/'rooter')

    def test_blank_data_root_does_not_overwrite(self):
        self.configure(data_root=str(self.data));before=self.install.read_bytes()
        with self.assertRaises(InstallationProblem):self.configure(data_root='')
        self.assertEqual(before,self.install.read_bytes())

    def test_corrupt_descriptor_does_not_overwrite(self):
        self.install.write_text('{broken',encoding='utf-8')
        with self.assertRaises(InstallationProblem):self.configure(data_root=str(self.data))
        self.assertEqual(self.install.read_text(),'{broken')

    def test_missing_registry_read_creates_nothing(self):
        missing=self.root/'missing'/'data';self.configure(data_root=str(missing))
        with self.assertRaises(RegistryProblem):ProjectRegistry(self.install).read('3002')
        self.assertFalse(missing.exists())

    def test_source_checkout_is_never_registry_fallback(self):
        decoy=self.source/'private-data'/'project-registry'/'projects';decoy.mkdir(parents=True)
        (decoy/'3002.json').write_text('{}',encoding='utf-8')
        self.configure(data_root=str(self.data))
        with self.assertRaises(RegistryProblem) as e:ProjectRegistry(self.install).read('3002')
        self.assertEqual(e.exception.code,'project_not_registered')

    def test_backup_restore_uses_registered_data_not_checkout(self):
        (self.data/'fact.txt').write_text('canonical',encoding='utf-8')
        archive=self.root/'backup.zip'
        create_backup(self.source,archive,data_root=self.data)
        target=self.root/'restored';restore_backup(self.source,archive,data_root=target)
        self.assertEqual((target/'fact.txt').read_text(),'canonical')
        self.assertFalse((self.source/'private-data').exists())

    def test_backup_cli_uses_installation_data(self):
        self.configure(data_root=str(self.data))
        (self.data/'fact.txt').write_text('canonical',encoding='utf-8')
        decoy=self.source/'private-data';decoy.mkdir();(decoy/'wrong.txt').write_text('decoy')
        archive=self.root/'backup.zip'
        env=dict(os.environ,PAOS_INSTALLATION_FILE=str(self.install),PYTHONIOENCODING='utf-8')
        r=subprocess.run([sys.executable,str(ROOT/'scripts/paos_backup.py'),'backup','--repo-root',str(self.source),'--output',str(archive)],env=env,capture_output=True,text=True,encoding='utf-8',timeout=10)
        self.assertEqual(r.returncode,0,r.stderr)
        with zipfile.ZipFile(archive) as z:
            self.assertIn('private-data/fact.txt',z.namelist())
            self.assertFalse(any('wrong.txt' in name for name in z.namelist()))


if __name__=='__main__':unittest.main()
