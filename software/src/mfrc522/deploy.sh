#!/usr/bin/bash
set -eu

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

MFRC522_LIBDIR=$(readlink -f "$SCRIPT_DIR"/../../lib/micropython-mfrc522)

error_exit()
{
    MESSAGE="$1"

    echo "Error: $MESSAGE"
    echo "Exit."
    exit 1
}

check_command()
{
    CMD="$1"

    if ! command -v "$CMD" 2>&1 >/dev/null
    then
        error_exit "'$CMD' not found."
    fi
}

check_command mpremote

mpremote fs cp "$MFRC522_LIBDIR/mfrc522.py" ":mfrc522.py"

mpremote reset

echo "Library deployed. Run main.py with 'mpremote run main.py'"
