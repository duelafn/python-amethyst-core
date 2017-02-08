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
import re

__version__ = re.search(r'(?m)^__version__\s*=\s*"([\d.]+(?:[\-\+~.]\w+)*)"', open('amethyst/core/__init__.py').read()).group(1)

from setuptools import setup

import unittest
def my_test_suite():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    return test_suite

setup(
    name         = 'amethyst-core',
    version      = __version__,
    url          = 'https://github.com/duelafn/python-amethyst-core',
    author       = "Dean Serenevy",
    author_email = 'dean@serenevy.net',
    description  = "A sober python base library",
    packages     = [ 'amethyst.core' ],
    requires     = [ "six", ],
    namespace_packages = [ 'amethyst' ],
    test_suite   = 'setup.my_test_suite',
)
