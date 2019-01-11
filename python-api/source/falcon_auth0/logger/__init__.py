# System Imports
from __future__ import division, unicode_literals
import logging

# Third-Party Imports

# Local Source Imports

__author__ = 'H.D. "Chip" McCullough IV'

logger = logging.getLogger('falcon-auth0')
logger.setLevel(logging.WARNING)
logger.addHandler(logging.NullHandler())