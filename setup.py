#!/usr/bin/env python
"""
A sober python base library
"""
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

import io
import re
import setuptools
import unittest

__version__ = re.search(r'(?m)^__version__\s*=\s*"([\d.]+(?:[\-\+~.]\w+)*)"', open('amethyst/core/__init__.py').read()).group(1)

def my_test_suite():
    return unittest.TestLoader().discover('tests', pattern='test_*.py')

with io.open('README.rst', encoding='UTF-8') as fh:
    readme = fh.read()

setuptools.setup(
    name         = 'amethyst-core',
    version      = __version__,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        ],
    url          = 'https://github.com/duelafn/python-amethyst-core',
    author       = "Dean Serenevy",
    author_email = 'dean@serenevy.net',
    description  = "A sober python base library",
    long_description = readme,
    packages     = setuptools.find_packages(),
    requires     = [ "six", ],
    install_requires = [ 'setuptools' ],
    namespace_packages = [ 'amethyst' ],
    test_suite   = 'setup.my_test_suite',
)
