#!/usr/bin/env bash
# Установка secbox. Запускает сам владелец: bash setup.sh
# Ничего не шифрует и не спрашивает паролей — только раскладывает файлы по местам.
set -eu
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

chmod 700 "$DIR/bin/sec" "$DIR/bin/secscan"
mkdir -p "$HOME/bin"
ln -sfn "$DIR/bin/sec" "$HOME/bin/sec"
ln -sfn "$DIR/bin/secscan" "$HOME/bin/secscan"

mkdir -p "$HOME/.secrets"
chmod 700 "$HOME/.secrets"

# в git такое не должно уехать никогда
if [ -d "$DIR/.git" ] || [ -d "$HOME/projects/.git" ]; then
  printf '%s\n' '.secrets/' 'vault.gpg*' 'staging.json' > "$DIR/.gitignore"
fi

echo "✓ установлено:"
echo "    sec      → $DIR/bin/sec"
echo "    secscan  → $DIR/bin/secscan"
echo "    ~/.secrets (0700) создан"
echo
echo "Дальше по шагам:"
echo "  1) secscan            — посмотреть, что вообще лежит открытым (значения маскированы)"
echo "  2) sec init           — спросит мастер-пароль ДВАЖДЫ и запакует найденное"
echo "  3) sec ls             — проверить список ключей"
echo "  4) sec sources        — где те же секреты всё ещё лежат в открытую"
