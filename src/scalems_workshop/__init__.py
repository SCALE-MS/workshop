"""SCALE-MS data flow scripting for adaptive ensemble workflows.

This package lives at https://github.com/SCALE-MS/workshop
"""

__all__ = ['__version__',
           'executable',
           'less_than',
           'logical_not',
           'numeric_min',
           'output_file',
           'while_loop',
           'xvg_to_array']

from importlib.metadata import version

from .commands.executable import executable
from .helpers import less_than
from .helpers import numeric_min
from .helpers import xvg_to_array
from .subgraph import logical_not
from .subgraph import while_loop
from .util import output_file

__version__ = version("scalems_workshop")
