
VENV ?= venv
PYTHON_BIN ?= python3.10
PYTHON ?= $(VENV)/bin/python
PYTHONPATH = $(VENV)/lib/$(PYTHON_BIN)/site-packages:backend
PORT ?= 8006


run: venv
	$(VENV)/bin/uvicorn --factory snapshot_manager.app:get_app \
		--reload --reload-dir backend/snapshot_manager --port $(PORT)


venv: backend/requirements.txt
	$(PYTHON_BIN) -m venv $(VENV)
	$(VENV)/bin/pip install -r backend/requirements.txt
	touch venv


backend/requirements.txt: backend/requirements.in
	pip-compile --output-file backend/requirements.txt backend/requirements.in
