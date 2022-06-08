"""SCALE-MS data flow scripting for adaptive ensemble workflows.

This package lives at https://github.com/SCALE-MS/workshop
"""

__all__ = ['__version__', 'less_than', 'numeric_min', 'xvg_to_array']

import logging
import typing
from importlib.metadata import version

import gmxapi
import gmxapi.abc

__version__ = version("scalems_workshop")


class UsageError(Exception):
    """A module feature is being misused."""


def function_wrapper(*args, **kwargs):
    return gmxapi.function_wrapper(*args, **kwargs)


def less_than(lhs: typing.SupportsFloat, rhs: typing.SupportsFloat):
    """Compare the left-hand-side to the right-hand-side.

    Follows the Numpy logic for normalizing the numeric types of *lhs* and *rhs*.
    """
    import numpy as np
    dtype = int
    if any(isinstance(operand, float) for operand in (lhs, rhs)):
        dtype = float
    elif all(isinstance(operand, typing.SupportsFloat) for operand in (lhs, rhs)):
        if type(np.asarray([lhs, rhs])[0].item()) is float:
            dtype = float
    elif any(isinstance(operand, gmxapi.abc.Future) for operand in (lhs, rhs)):
        for item in (lhs, rhs):
            if hasattr(item, 'dtype'):
                if issubclass(item.dtype, (float, np.float)):
                    dtype = float
            elif hasattr(item, 'description'):
                if issubclass(item.description.dtype, (float, np.float)):
                    dtype = float
    else:
        raise UsageError(f'No handling for [{repr(lhs)}, {repr(rhs)}].')

    if dtype is int:
        def _less_than(lhs: int, rhs: int) -> bool:
            return lhs < rhs
    elif dtype is float:
        def _less_than(lhs: float, rhs: float) -> bool:
            return lhs < rhs
    else:
        raise UsageError('Operation only supports standard numeric types.')
    return function_wrapper()(_less_than)(lhs=lhs, rhs=rhs)


@function_wrapper()
def _numpy_min_float(data: gmxapi.NDArray) -> float:
    import numpy as np
    logging.info(f'Looking for minimum in {data}')
    return float(np.min(data._values))


def numeric_min(array):
    """Find the minimum value in an array.
    """
    return _numpy_min_float(data=array)


@function_wrapper(output={'data': gmxapi.NDArray})
def xvg_to_array(path: str, output):
    """Get an NxM array from a GROMACS xvg data file.

    For energy output, N is the number of samples, and the first of M
    columns contains simulation time values.
    """
    import numpy
    logging.info(f'Reading xvg file {path}.')
    data = numpy.genfromtxt(path, comments='@', skip_header=14)
    logging.info(f'Read array shape {data.shape} from {path}.')
    if len(data.shape) == 1:
        # Trajectory was too short. Only a single line was read.
        assert data.shape[0] == 2
        data = data.reshape((1, 2))
    assert len(data.shape) == 2
    output.data = data[:, 1]
