# RAGBench developer commands. On Windows, run the underlying python commands
# directly if `make` is unavailable (see README).

.PHONY: install lint test ingest query stats serve all

install:
	python -m pip install -e ".[dev]"

lint:
	python -m ruff check .

test:
	python -m pytest

ingest:
	python -m ragbench.cli ingest evaluation/datasets/corpus

query:
	python -m ragbench.cli query "What is reciprocal rank fusion?" --strategy hybrid

stats:
	python -m ragbench.cli stats

serve:
	uvicorn ragbench.api.app:app --reload

all: lint test
