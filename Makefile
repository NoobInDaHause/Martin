.PHONY: reformat check-syntax install-dependencies, install-black

reformat:
	autoflake --remove-all-unused-imports --recursive --in-place .
	isort .
	black .

check-syntax:
	python -m compileall .

install-dependencies:
	python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

install-black:
	python -m pip install black isort autoflake