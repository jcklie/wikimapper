test:
	python -m pytest tests/

black:
	black -l 100 wikimapper/
	black -l 100 tests/

isort:
	isort --profile black wikimapper/ tests/

format: black isort

html:
	cd docs && make html