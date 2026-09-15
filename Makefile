PYTHON ?= python3
.PHONY: install setup run test check ui-test
install:
	$(PYTHON) -m pip install -r requirements.txt
setup:
	$(PYTHON) scripts/setup.py
run:
	$(PYTHON) scripts/run.py
test:
	$(PYTHON) -m pytest -q
check:
	$(PYTHON) -m compileall -q backend hermes scripts
	node scripts/check_frontend.mjs
ui-test:
	$(PYTHON) scripts/test_ui.py
