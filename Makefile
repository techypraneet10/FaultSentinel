.PHONY: setup test lint help

PYTHON ?= python

help:
	@echo SentinelLog Development Commands:
	@echo   make setup - Install pinned dependencies from requirements.txt
	@echo   make test  - Run pytest test suite
	@echo   make lint  - Run lightweight syntax and static compilation check

setup:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest -v tests

lint:
	$(PYTHON) -m compileall -q sentinellog tests
