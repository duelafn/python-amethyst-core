# SPDX-License-Identifier: LGPL-3.0

PKGNAME = amethyst-core
PKG_VERSION = $(shell python -c 'import re; print(re.search("__version__ = \"([\d.]+)\"", open("amethyst/core/__init__.py").read()).group(1))')
PY_PATHS = tests amethyst

VSDIST_TAR_GZ=dist/${PKG_VERSION}/${PKGNAME}-${PKG_VERSION}.tar.gz

.PHONY: all sdist dist debbuild clean test doc


check::
	python3 -m flake8 --config=extra/flake8.ini ${PY_PATHS}
	@echo OK

clean:
	rm -rf build dist debbuild _doc .tox amethyst_core.egg-info
	rm -f MANIFEST
	python3 setup.py clean

doc:
	sphinx-build -q -n -E -b singlehtml doc _doc/html

publish-test:
	python3 -m twine upload --repository testpypi dist/${PKG_VERSION}/*.whl ${VSDIST_TAR_GZ}

publish:
	python3 -m twine upload --repository pypi dist/${PKG_VERSION}/*.whl ${VSDIST_TAR_GZ}

sdist: test
	python3 setup.py sdist

test:
	python3 -m pytest --cov=amethyst/ --cov-branch --cov-report=html:_coverage tests

test-pypy:
	for f in tests/test_*.py; do pypy3 -E -B "$$f"; done

wheel:
	python3 setup.py bdist_wheel

zip: test
	python3 setup.py sdist --format=zip


# Optionally include Makefile.local for per-developer make targets
-include Makefile.local
