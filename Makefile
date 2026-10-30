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

SCENARIO ?= port_delay_low
PERSONA ?= plant
ARCH ?= sequential
STRATEGY ?= react
COMM_MODE ?= blackboard
SCOUT_PROMPT ?= scout_cot_v1
export PYTHONPATH := .
export PYTHONUTF8 := 1
export CREWAI_TRACING_ENABLED := false
export OTEL_SDK_DISABLED := true

.PHONY: view poison inventory vendors docs forecast rag-probe check setup up down test news-snapshot m5-extract data rag-index run-one pilot report schemas

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

vendors:
	$(PY_PLATFORM) data/synth/build_vendors.py

docs:
	$(PY_PLATFORM) data/synth/build_docs.py

forecast:
	$(PY_PLATFORM) data/forecasting/build_baselines.py

rag-index:
	$(PY_PLATFORM) data/rag/build_index.py

rag-probe:
	$(PY_PLATFORM) data/rag/probe.py

data: m5-extract inventory vendors docs forecast rag-index

news-snapshot:
	$(PY_SENSING) -m sensing.news.fetch

up:
	$(PY_PLATFORM) deploy/services.py up

down:
	$(PY_PLATFORM) deploy/services.py down

check:
	$(PY_PLATFORM) deploy/services.py check

run-one:
	$(PY_SENSING) eval/run_one.py --scenario $(SCENARIO) --persona $(PERSONA) --arch $(ARCH) --strategy $(STRATEGY) --comm-mode $(COMM_MODE) --scout-prompt $(SCOUT_PROMPT)

view:
	$(PY_PLATFORM) -m scout_platform.tracing.view $(RUN)

poison:
	$(PY_SENSING) eval/poison_test.py

pilot report:
	@echo "$@ is not built yet; see SCOUT_IMPLEMENTATION_PLAN.md" && exit 1
