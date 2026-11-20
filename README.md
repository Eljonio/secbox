# secbox

[![tests](https://github.com/Eljonio/secbox/actions/workflows/test.yml/badge.svg)](https://github.com/Eljonio/secbox/actions/workflows/test.yml)

A personal secrets safe built for working next to an AI coding agent: the agent can **use** a password or a
token without ever **seeing** it, and the master password never passes through the agent's context.

Two small Python scripts, no pip dependencies: `sec` (the safe) and `secscan` (finds secrets lying around in
plain text and moves them into the safe).

## The problem

A coding agent reads notes, `.env` files and shell output, and everything it reads becomes part of the
conversation. Passwords written in notes get repeated back, pasted into commands and stored in transcripts.
Telling the agent "don't print secrets" does not help when the secret is already in the file it was asked to read.

secbox changes what the agent has access to:

- secrets live in one encrypted file, and notes refer to them by key name;
- the commands the agent is expected to use never print a value: `sec env` puts it into an environment variable
  of one command, `sec ssh` passes it to `sshpass`, `sec cp` puts it into the clipboard;
- the master password is asked by a pinentry window (or the terminal), is never a command-line argument and is
  never printed, so it cannot end up in the transcript;
- decrypted data exists only in RAM (`/dev/shm`, mode 0600) for a limited time and is overwritten on lock.

## Where to look first

| to check | open |
|---|---|
| how the master password is asked without passing through argv or the agent | `ask_pass` and `run_pipe` in [`bin/sec`](bin/sec) |
| encryption: age (X25519) for the safe, GnuPG symmetric AES-256 for the identity | `gpg_seal`, `age_encrypt`, `save_locked` in [`bin/sec`](bin/sec) |
| the timed unlock in RAM and how it is wiped | `cmd_unlock`, `cmd_reaper`, `shred` in [`bin/sec`](bin/sec) |
| using a secret without printing it | `cmd_env`, `cmd_ssh`, `cmd_cp` in [`bin/sec`](bin/sec) |
| the scanner: named parameters, known token formats, noise filter, masked output | [`bin/secscan`](bin/secscan) |
| the end-to-end test on a throwaway safe | [`tests/test_smoke.py`](tests/test_smoke.py) — `python3 -m unittest discover -s tests` |

## How it works

```
plain-text secrets in notes, .env, configs
        │  secscan  (masked report; full values go to a staging file in RAM)
        ▼
sec init ──► ~/.secrets/vault.age        all entries, encrypted to an age X25519 recipient
             ~/.secrets/identity.gpg     the age identity, sealed with the master password (GnuPG, AES-256)
             ~/.secrets/catalog          key names only

sec unlock 15 ──► /dev/shm/secbox-<uid>/unlocked.json  (0600, wiped by a timer or `sec lock`)
        │
        ├─ sec env VAR=key -- command     the value goes into one process's environment
        ├─ sec ssh key user@host          the value goes to sshpass through the environment
        └─ sec cp key                     the value goes to the clipboard
```

Three ways to protect the identity:

| mode | what is needed to open the safe |
|---|---|
| `pass` (default) | the master password |
| `usb` | a specific USB drive holding the identity file |
| `usb+pin` | the USB drive and a short PIN; a long recovery password covers a lost drive (`sec recover`) |

## Commands

```
sec init [--usb] [--no-pin]    create the safe (takes the scanner's findings if there are any)
sec unlock [minutes]           open access (15 minutes by default, 480 at most)
sec lock                       close and wipe the decrypted copy
sec status                     mode, locked/unlocked, time left
sec ls [filter]                key names, no values
sec show <key>                 source and length, no value
sec cp <key>                   value to the clipboard
sec env VAR=key [..] -- cmd    run a command with the secret in a variable
sec ssh <key> user@host [..]   ssh through sshpass
sec get <key>                  print the value (deliberately)
sec add <key> [--note text]    add an entry (the value is typed hidden)
sec rm <key> | sec rename <old> <new>
sec passwd | sec recover | sec export <file>
sec sources                    files on disk that still contain these secrets in plain text

secscan                        scan and print a masked report
```

## Install

Linux. Needs Python 3, [`age`](https://github.com/FiloSottile/age) and GnuPG; optional: `pinentry` or `zenity`
(password window), `sshpass` (`sec ssh`), `xclip` / `wl-copy` / `xsel` (`sec cp`).

```bash
sudo apt install age gnupg sshpass xclip
bash setup.sh        # links sec and secscan into ~/bin, creates ~/.secrets (0700)
secscan              # see what lies in plain text (values are masked)
sec init             # asks for the master password twice
```

`secscan` looks in a fixed list of places under the home directory (`ROOTS` at the top of the script);
edit it for your own layout.

## Tests

```bash
pip install pexpect   # only for the test
python3 -m unittest discover -s tests
```

One end-to-end test on a throwaway safe (temporary `HOME`, separate RAM directory): create, add a key, check
that the value is not on disk in plain text and is not printed by `ls` / `show` / `status`, reject a wrong master
password, unlock, pass the secret to a command through `sec env`, lock.

## Limitations

- **It is a convention, not isolation.** While the safe is unlocked, the decrypted file in `/dev/shm` is readable
  by any process of the same user, including the agent. secbox keeps secrets out of the transcript when the agent
  uses `sec env` / `sec ssh` / `sec cp`; it does not stop an agent that decides to read that file or to run
  `sec get`.
- Only the password mode is covered by the test. The USB modes, `passwd`, `recover`, `export`, `cp`, `ssh` and
  `secscan` have no automated tests.
- A secret passed with `sec env` is visible to that command and its children; `sec ssh` disables host key checking.
- Wiping overwrites the file twice before deleting it; on tmpfs that is RAM, on a USB flash drive it is best effort.
- Linux only. Messages and comments are in Russian.

**Provenance.** Exported on 2026-11-20 from a private working copy. The owner's name and a personal folder in the
scan list were removed, so the public history starts with the export.

## License

MIT, see [LICENSE](LICENSE).
