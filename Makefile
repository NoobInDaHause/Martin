.PHONY: reformat

reformat:
	autoflake --remove-all-unused-imports --recursive --in-place .
	isort .
	black .