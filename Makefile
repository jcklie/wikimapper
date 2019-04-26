test:
	python -m pytest tests/

black:
	black -l 100 wikimapper/
	black -l 100 tests/

html:
	cd docs && make html