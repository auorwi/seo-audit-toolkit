import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from toolkit.runtime import doctor


class RuntimeTests(unittest.TestCase):
    def test_existing_interpreter_without_extruct_is_not_ready(self):
        with tempfile.TemporaryDirectory() as d:
            python = Path(d) / 'structured/bin/python'
            venv.EnvBuilder(with_pip=False).create(Path(d) / 'structured')
            result = doctor(d)
            self.assertTrue(result['base_ready'])
            self.assertFalse(result['structured']['installed'])
            self.assertFalse(result['structured']['ready'])
            self.assertTrue(result['structured']['interpreter_present'])
            self.assertIn('extruct', result['structured']['diagnostic'])

    def test_structured_probe_timeout_and_invalid_executable_are_localized(self):
        for error in (subprocess.TimeoutExpired(['python'], 10), OSError('not executable')):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as d:
                python = Path(d) / 'structured/bin/python'
                python.parent.mkdir(parents=True)
                python.touch()
                with patch('toolkit.runtime.shutil.which', return_value=None), patch('toolkit.runtime.subprocess.run', side_effect=error):
                    result = doctor(d)
                self.assertTrue(result['base_ready'])
                self.assertFalse(result['structured']['ready'])
                self.assertTrue(result['structured']['diagnostic'])

    def test_structured_probe_requires_import_and_version_result(self):
        with tempfile.TemporaryDirectory() as d:
            python = Path(d) / 'structured/bin/python'
            python.parent.mkdir(parents=True)
            python.write_text('#!' + sys.executable + '\nimport json, sys\nexec(sys.argv[2])\n')
            python.chmod(0o755)
            # The fake installed package lives only in the selected interpreter environment.
            package = python.parent / 'extruct.py'
            package.write_text('def extract(*args, **kwargs): return {}\n')
            (python.parent / 'extruct-0.18.0.dist-info').mkdir()
            (python.parent / 'extruct-0.18.0.dist-info/METADATA').write_text('Name: extruct\nVersion: 0.18.0\n')
            result = doctor(d)
            self.assertTrue(result['structured']['installed'])
            self.assertTrue(result['structured']['ready'])
            self.assertEqual(result['structured']['version'], '0.18.0')
