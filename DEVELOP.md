# Developer notes

## How to setup python environment for mypy and pytest

```bash
cd software
python -m venv test-venv
. test-venv/bin/activate
pip install -r tests/requirements.txt
pip install -U micropython-rp2-pico_w-stubs --target typings
```
