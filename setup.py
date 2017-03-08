# coding: utf-8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)

import re
import setuptools


def get_version(path="src/pypnusershub/__init__.py"):
    """ Return the version of by with regex intead of importing it"""
    init_content = open(path, "rt").read()
    pattern = r"^__version__ = ['\"]([^'\"]*)['\"]"
    return re.search(pattern, init_content, re.M).group(1)


setuptools.setup(
    name='pypnusershub',
    version=get_version(),
    description="Python lib to authenticate using PN's UsersHub",
    long_description=open('README.md').read().strip(),
    author="Les parcs nationaux de France",
    url='https://github.com/PnX-SI/UsersHub-authentification-module',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    install_requires=list(open('requirements.txt')),
    include_package_data=True,
    zip_safe=False,
    keywords='ww',
    classifiers=['Development Status :: 1 - Planning',
                 'Intended Audience :: Developers',
                 'Natural Language :: English',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'License :: OSI Approved :: GNU Affero General Public License v3'
                 'Operating System :: OS Independent'],
)
