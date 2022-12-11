
VENV ?= venv
PYTHON_BIN ?= python3.10
PYTHON ?= $(VENV)/bin/python
PYTHONPATH = $(VENV)/lib/$(PYTHON_BIN)/site-packages:backend
PORT ?= 8006


run: venv frontend/kube-snapshot-manager/build
	$(VENV)/bin/uvicorn --factory snapshot_manager.app:get_app \
		--reload --reload-dir backend/snapshot_manager \
		--port $(PORT) --host ::0


venv: backend/requirements.txt
	$(PYTHON_BIN) -m venv $(VENV)
	$(VENV)/bin/pip install -r backend/requirements.txt
	touch venv


backend/requirements.txt: backend/requirements.in
	pip-compile --output-file backend/requirements.txt backend/requirements.in


frontend/kube-snapshot-manager/build: frontend/kube-snapshot-manager/node_modules
	cd frontend/kube-snapshot-manager && pnpm run build


frontend/kube-snapshot-manager/node_modules: frontend/kube-snapshot-manager/pnpm-lock.yaml
	cd frontend/kube-snapshot-manager && pnpm install
