.PHONY: reformat check-syntax

reformat:
	autoflake --remove-all-unused-imports --recursive --in-place .
	isort .
	black .

check-syntax:
	python -m compileall .