REPO=testpypi

all:
	rm -rf dist
	rm -rf build
	python setup.py sdist
	twine upload --repository $(REPO) dist/*
