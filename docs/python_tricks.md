# Python Tricks

## start terminal with virtual environment

```bash
source .venv/bin/activate
```

## deactivate virtual environment

```bash
deactivate
```

## run test suite

```bash
python -m pytest -v 
```
## run test suite with coverage

```bash
python -m pytest -v --cov=recap --cov=aiapi
```

## run test suite with coverage and html report

```bash
python -m pytest -v --cov=recap --cov=aiapi --cov-report=html
```