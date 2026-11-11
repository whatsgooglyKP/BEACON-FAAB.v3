# Beacon evaluation lab shortcuts (the app itself still runs from app/ with npm).
.PHONY: evals evals-live evals-test
evals:
	python3 -m evals.run --all
evals-live:
	python3 -m evals.run --all --live
evals-test:
	python3 -m unittest discover -s evals/tests -t . -v
