# Author: Dean Serenevy <dean@serenevy.net>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

PKGNAME = amethyst-core
PKG_VERSION = $(shell python -c 'import re; print(re.search("__version__ = \"([\d.]+)\"", open("amethyst/core/__init__.py").read()).group(1))')

.PHONY: all sdist dist debbuild clean test


test:
	tox

check:
	python3 -m flake8 --config=extra/flake8.ini amethyst/core/*.py
	python2 -m flake8 --config=extra/flake8.ini amethyst/core/*.py
	@echo OK

zip: test
	python3 setup.py sdist --format=zip

sdist: test
	python3 setup.py sdist

dist: test debbuild
	mv -f debbuild/${PKGNAME}_* debbuild/*.deb dist/
	rm -rf debbuild

debbuild: test sdist
	grep "(${PKG_VERSION}-1)" debian/changelog || (echo "** debian/changelog requires update **" && false)
	rm -rf debbuild
	mkdir -p debbuild
	mv -f dist/${PKGNAME}-${PKG_VERSION}.tar.gz debbuild/${PKGNAME}_${PKG_VERSION}.orig.tar.gz
	cd debbuild && tar -xzf ${PKGNAME}_${PKG_VERSION}.orig.tar.gz
	cp -r debian debbuild/${PKGNAME}-${PKG_VERSION}/
	cd debbuild/${PKGNAME}-${PKG_VERSION} && dpkg-buildpackage -rfakeroot -uc -us

clean:
	pyclean .
	rm -rf build dist debbuild
	rm -f MANIFEST
