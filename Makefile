# One-command build. Uses .venv/bin/python if it exists, else python on PATH.
PY ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python)
NOTEBOOKS := $(sort $(wildcard notebooks/0*.ipynb))

.PHONY: all data report notebooks app test screenshots clean

## all: data -> analysis -> figures -> report.html -> executed notebooks + HTML exports
all: data report notebooks

## data: clean, quality checks, SQL KPIs, root cause, synthetic scale-up, staffing model, business case
data:
	$(PY) run.py --skip-report

## report: reports/report.html + reports/figures/*.png
report:
	$(PY) -c "from support_ops import report; report.build()"

## notebooks: execute every notebook top to bottom, save outputs, export HTML to reports/
notebooks:
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 $(NOTEBOOKS)
	$(PY) -m jupyter nbconvert --to html --output-dir reports $(NOTEBOOKS)

## app: start the Streamlit demo app
app:
	$(PY) -m streamlit run dashboard/app.py

## test: unit tests (Erlang C, simulation, what-if functions)
test:
	$(PY) -m pytest -q

## screenshots: regenerate docs/img/*.png (needs requirements-dev.txt + playwright install chromium)
screenshots:
	$(PY) scripts/take_screenshots.py

clean:
	rm -rf data/processed
