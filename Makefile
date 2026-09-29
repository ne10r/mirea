.PHONY: run test

run:
	./run.sh

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
