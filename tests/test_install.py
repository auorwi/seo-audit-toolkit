import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='seo install ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'downloaded source'
        (self.source / 'skills' / 'seo-demo').mkdir(parents=True)
        (self.source / 'skills' / 'seo-demo' / 'SKILL.md').write_text('demo')
        (self.source / 'VERSION').write_text('0.1.0\n')
        (self.source / 'seo.py').write_text('print("demo")\n')
        self.target = self.base / 'managed'
        self.skills = self.base / 'skills'

    def load(self):
        self.assertTrue((ROOT / 'install.py').is_file(), 'A downloaded ZIP needs an installer')
        spec = importlib.util.spec_from_file_location('seo_installer', ROOT / 'install.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_install_relocatable_idempotent_and_uninstall_preserves_data(self):
        installer = self.load()
        result = installer.install(self.source, self.target, self.skills)
        link = self.skills / 'seo-demo'
        self.assertTrue(link.is_symlink())
        self.assertEqual((link / 'SKILL.md').read_text(), 'demo')
        self.assertNotIn(str(self.source), str(link.resolve()))
        self.assertEqual(installer.install(self.source, self.target, self.skills), result)
        (self.target / 'data').mkdir()
        (self.target / 'data' / 'history.json').write_text('{"issues":1}')
        other = self.skills / 'other'
        other.mkdir()
        installer.uninstall(self.target, self.skills)
        self.assertFalse(link.exists())
        self.assertTrue(other.is_dir())
        self.assertTrue((self.target / 'data' / 'history.json').is_file())

    def test_conflicting_skill_is_never_overwritten(self):
        installer = self.load()
        (self.skills / 'seo-demo').mkdir(parents=True)
        (self.skills / 'seo-demo' / 'mine').write_text('keep')
        with self.assertRaises(ValueError):
            installer.install(self.source, self.target, self.skills)
        self.assertEqual((self.skills / 'seo-demo' / 'mine').read_text(), 'keep')

    def test_unmanaged_link_to_cwd_is_never_overwritten(self):
        self.skills.mkdir()
        link = self.skills / 'seo-demo'
        link.symlink_to(Path.cwd(), target_is_directory=True)
        original = os.readlink(link)
        with self.assertRaisesRegex(ValueError, 'Unmanaged skill'):
            self.load().install(self.source, self.target, self.skills)
        self.assertEqual(os.readlink(link), original)

    def test_uninstall_does_not_remove_replaced_link(self):
        installer = self.load()
        installer.install(self.source, self.target, self.skills)
        link = self.skills / 'seo-demo'
        link.unlink()
        other = self.base / 'replacement'
        other.mkdir()
        link.symlink_to(other, target_is_directory=True)
        installer.uninstall(self.target, self.skills)
        self.assertEqual(link.resolve(), other.resolve())

    def test_upgrade_retargets_managed_links_and_keeps_old_version(self):
        installer = self.load()
        installer.install(self.source, self.target, self.skills)
        old = (self.skills / 'seo-demo').resolve()
        (self.source / 'skills' / 'seo-demo' / 'SKILL.md').write_text('updated')
        installer.install(self.source, self.target, self.skills)
        self.assertEqual((self.skills / 'seo-demo' / 'SKILL.md').read_text(), 'updated')
        self.assertEqual((old / 'SKILL.md').read_text(), 'demo')

    def test_source_symlink_cannot_copy_external_files(self):
        installer = self.load()
        outside = self.base / 'private'
        outside.write_text('do not copy')
        (self.source / 'skills' / 'seo-demo' / 'secret').symlink_to(outside)
        with self.assertRaises(ValueError):
            installer.install(self.source, self.target, self.skills)

    def test_manifest_path_traversal_cannot_unlink_unrelated_path(self):
        installer = self.load()
        installer.install(self.source, self.target, self.skills)
        manifest = self.target / 'install-manifest.json'
        value = json.loads(manifest.read_text())
        value['links']['../victim'] = str(self.source)
        manifest.write_text(json.dumps(value))
        victim = self.base / 'victim'
        victim.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.uninstall(self.target, self.skills)
        self.assertTrue(victim.is_symlink())


if __name__ == '__main__':
    unittest.main()
