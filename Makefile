# RAGBench developer commands. On Windows, run the underlying python commands
# directly if `make` is unavailable (see README).

.PHONY: install lint format test security report ingest query stats serve version clean all

install:
	python -m pip install -e ".[dev]"

lint:
	python -m ruff check .

format:
	python -m ruff check --fix .

test:
	python -m pytest

security:
	python -m pytest tests/integration/test_api_security.py -q

report:
	python -m ragbench.cli evaluate --dataset evaluation/datasets/benchmark_v1.json --k 5

version:
	python -m ragbench.cli version

clean:
	python -c "import shutil,glob,os; [shutil.rmtree(p,ignore_errors=True) for p in glob.glob('**/__pycache__',recursive=True)+['.pytest_cache','.ruff_cache','build','ragbench.egg-info']]"

ingest:
	python -m ragbench.cli ingest evaluation/datasets/corpus

query:
	python -m ragbench.cli query "What is reciprocal rank fusion?" --strategy hybrid

stats:
	python -m ragbench.cli stats

serve:
	uvicorn ragbench.api.app:app --reload

all: lint test
