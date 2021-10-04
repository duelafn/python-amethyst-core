# SPDX-License-Identifier: LGPL-3.0

PKGNAME = amethyst-core
PKG_VERSION = $(shell python -c 'import re; print(re.search("__version__ = \"([\d.]+)\"", open("amethyst/core/__init__.py").read()).group(1))')
PY_PATHS = tests amethyst

SDIST_TAR_GZ=dist/${PKGNAME}-${PKG_VERSION}.tar.gz
VSDIST_TAR_GZ=dist/${PKG_VERSION}/${PKGNAME}-${PKG_VERSION}.tar.gz

.PHONY: all sdist dist debbuild clean test doc


check:
	python3 -m flake8 --config=extra/flake8.ini ${PY_PATHS}
	@echo OK

clean:
	rm -rf build dist debbuild _doc .tox amethyst_core.egg-info
	rm -f MANIFEST
	python3 setup.py clean

debbuild: test sdist
	@head -n1 debian/changelog | grep "(${PKG_VERSION}-1)" debian/changelog || (/bin/echo -e "\e[1m\e[91m** debian/changelog requires update **\e[0m" && false)
	rm -rf debbuild
	mkdir -p debbuild
	cp -f ${SDIST_TAR_GZ} debbuild/${PKGNAME}_${PKG_VERSION}.orig.tar.gz
	cd debbuild && tar -xzf ${PKGNAME}_${PKG_VERSION}.orig.tar.gz
	cp -r debian debbuild/${PKGNAME}-${PKG_VERSION}/
	cd debbuild/${PKGNAME}-${PKG_VERSION} && dpkg-buildpackage -rfakeroot -uc -us

dist: test debbuild wheel
	rm -rf dist/${PKG_VERSION}
	@mkdir -p dist/${PKG_VERSION}
	mv -f debbuild/${PKGNAME}_* debbuild/*.deb dist/${PKG_VERSION}/
	mv -f ${SDIST_TAR_GZ} dist/*.whl dist/${PKG_VERSION}/
	rm -rf debbuild

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

tox:
	tox

wheel:
	python3 setup.py bdist_wheel

zip: test
	python3 setup.py sdist --format=zip
