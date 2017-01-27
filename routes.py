# coding: utf8

"""
This module  was designed to be a submodule for
https://github.com/PnX-SI/TaxHub/.

In order to make it reusable, we turned it into a package, but TaxHub
still expects this file to exist and relies on it side effects. So we
make a fake module mimicing the previous one's behavior to maintain
compat.
"""

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)

import os
import sys

# The original lib contains a routes.py file at the root of the project
# where it defines "init_app()". It is expected to be called at the
# begining of the project to initialize the app.
from server import init_app

init_app()

# We then load the all namespaces so that if it's imported in any way, it's
# still available
CURDIR = os.path.dirname(os.path.abspath(__file__))
SRCDIR = os.path.join(CURDIR, 'src')

sys.path.append(SRCDIR)

from pypnuserhub.routes import *  # noqa
