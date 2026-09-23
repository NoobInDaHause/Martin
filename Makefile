.PHONY: style-reformat check-syntax install-dependencies install-dev-tools

install-dependencies:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

install-reformat-tools:
	python -m pip install black isort autoflake

style-reformat: install-reformat-tools
	autoflake --remove-all-unused-imports --recursive --in-place .
	isort .
	black .

check-syntax: install-dependencies
	python -m compileall -q -f .