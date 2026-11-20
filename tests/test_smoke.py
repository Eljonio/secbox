"""Сквозная проверка на одноразовом сейфе: подставной HOME и отдельная папка в RAM.
Настоящий ~/.secrets и /dev/shm/secbox-<uid> не затрагиваются."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import pexpect
except ImportError:  # pragma: no cover
    pexpect = None

SEC = str(Path(__file__).resolve().parents[1] / "bin" / "sec")
MASTER = "correct horse battery staple"
KEY = "demo.api_token"
SECRET = "s3cr3t-value-0123456789"
NEEDED = pexpect and all(shutil.which(t) for t in ("age", "age-keygen", "gpg"))


@unittest.skipUnless(NEEDED, "needs pexpect, age and gpg")
class Smoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="secbox-home-")
        cls.ram = tempfile.mkdtemp(prefix="secbox-test-", dir="/dev/shm" if os.path.isdir("/dev/shm") else None)
        cls.env = {**os.environ, "HOME": cls.home, "SECBOX_RAM_DIR": cls.ram}
        for var in ("DISPLAY", "WAYLAND_DISPLAY", "GNUPGHOME"):
            cls.env.pop(var, None)  # без GUI пароль спрашивается в терминале — его и подставляем

    @classmethod
    def tearDownClass(cls):
        subprocess.run([sys.executable, SEC, "lock"], env=cls.env, capture_output=True)
        subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=cls.env, capture_output=True)
        shutil.rmtree(cls.home, ignore_errors=True)
        shutil.rmtree(cls.ram, ignore_errors=True)

    def tty(self, args, answers):
        """Команда, которая спрашивает секреты в терминале."""
        child = pexpect.spawn(sys.executable, [SEC, *args], env=self.env, encoding="utf-8", timeout=180)
        out = ""
        for a in answers:
            child.expect(r": $")
            out += child.before
            child.sendline(a)
        child.expect(pexpect.EOF)
        out += child.before
        child.close()
        return child.exitstatus, out

    def sec(self, *args):
        r = subprocess.run([sys.executable, SEC, *args], env=self.env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout + r.stderr

    def test_full_cycle(self):
        secrets_dir = Path(self.home) / ".secrets"

        code, out = self.tty(["init"], [MASTER, MASTER])
        self.assertEqual(code, 0, out)
        vault = secrets_dir / "vault.age"
        self.assertTrue(vault.exists())
        self.assertEqual(oct(vault.stat().st_mode)[-3:], "600")

        code, out = self.tty(["add", KEY, "--note", "smoke"], [MASTER, SECRET])
        self.assertEqual(code, 0, out)
        self.assertNotIn(SECRET, out, "введённое значение не должно возвращаться на экран")

        # на диске: значение только внутри шифрованного файла, в каталоге — одни имена
        for f in secrets_dir.iterdir():
            self.assertNotIn(SECRET.encode(), f.read_bytes(), f"открытое значение в {f.name}")
        self.assertEqual((secrets_dir / "catalog").read_text().split(), [KEY])

        # заперто: имена видны, значения недоступны
        code, out = self.sec("ls")
        self.assertEqual(code, 0, out)
        self.assertIn(KEY, out)
        code, out = self.sec("env", f"TOKEN={KEY}", "--", "true")
        self.assertNotEqual(code, 0, "из запертого сейфа секрет выдаваться не должен")

        # неверный мастер-пароль не открывает
        code, out = self.tty(["unlock", "5"], ["wrong password"])
        self.assertNotEqual(code, 0, out)
        self.assertFalse((Path(self.ram) / "unlocked.json").exists())

        code, out = self.tty(["unlock", "5"], [MASTER])
        self.assertEqual(code, 0, out)

        # открыто: show / ls / status значение не печатают
        for cmd in (("show", KEY), ("ls",), ("status",)):
            code, out = self.sec(*cmd)
            self.assertEqual(code, 0, out)
            self.assertNotIn(SECRET, out, f"sec {cmd[0]} напечатал значение")

        # env: команда получает секрет в переменной, на экран он не выходит
        code, out = self.sec("env", f"TOKEN={KEY}", "--", "sh", "-c", f'[ "$TOKEN" = "{SECRET}" ]')
        self.assertEqual(code, 0, out)
        self.assertNotIn(SECRET, out)

        code, out = self.sec("lock")
        self.assertEqual(code, 0, out)
        self.assertFalse((Path(self.ram) / "unlocked.json").exists())
        code, out = self.sec("env", f"TOKEN={KEY}", "--", "true")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
