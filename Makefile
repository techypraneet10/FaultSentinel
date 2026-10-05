.PHONY: setup test lint help

PYTHON ?= python

help:
	@echo SentinelLog Development Commands:
	@echo   make setup    - Install pinned dependencies from requirements.txt
	@echo   make test     - Run pytest test suite
	@echo   make lint     - Run lightweight syntax and static compilation check
	@echo   make pipeline - Run Phase 2 data ingestion and windowing pipeline

setup:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -v tests

lint:
	$(PYTHON) -m compileall -q sentinellog tests scripts

pipeline:
	$(PYTHON) -m sentinellog.ingestion.pipeline --config configs/data_pipeline.yaml
