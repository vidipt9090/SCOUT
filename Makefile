# Requires GNU make and bash (Git Bash on Windows).
ifeq ($(OS),Windows_NT)
BIN := Scripts
else
BIN := bin
endif
PY_SENSING  := .venvs/sensing/$(BIN)/python
PY_DECISION := .venvs/decision/$(BIN)/python
PY_PLATFORM := .venvs/scout_platform/$(BIN)/python
PYTHON312 ?= python3.12

.PHONY: inventory setup up down test news-snapshot m5-extract data rag-index run-one pilot report schemas

setup:
	for s in sensing decision scout_platform; do \
		$(PYTHON312) -m venv .venvs/$$s && \
		.venvs/$$s/$(BIN)/python -m pip install -r $$s/requirements.txt || exit 1; \
	done

test:
	$(PY_PLATFORM) -m pytest

schemas:
	$(PY_PLATFORM) -m contracts.export_schemas

m5-extract:
	$(PY_PLATFORM) data/m5/extract.py

inventory:
	$(PY_PLATFORM) data/synth/build_inventory.py

up down news-snapshot data rag-index run-one pilot report:
	@echo "$@ is not built yet; see SCOUT_IMPLEMENTATION_PLAN.md" && exit 1
