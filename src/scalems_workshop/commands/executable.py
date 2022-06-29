"""Provide executable() command line wrapper."""

import collections.abc
import pathlib
import typing
from dataclasses import dataclass
from dataclasses import field
from typing import Optional
from typing import Sequence

import gmxapi
import gmxapi.abc
from gmxapi.operation import _OutputDataProxyType

from scalems_workshop._abc import Future
from scalems_workshop._abc import PlaceHolder
from scalems_workshop._abc import Reference
from scalems_workshop._abc import SupportsEnsemble
from scalems_workshop.exceptions import *
from scalems_workshop.util import get_path
from scalems_workshop.util import OutputFilePlaceholder

CommandLineArgvType = Sequence[typing.Union[str, pathlib.Path, Future[str], PlaceHolder[str]]]


@dataclass
class _ParsedArgs:
    executable: str
    arguments: typing.List[str] = field(default_factory=list)
    input_files: typing.Dict[str, typing.Union[Future[str], str]] \
        = field(default_factory=dict)
    output_files: typing.Dict[str, str] = field(default_factory=dict)


# class GmxapiResourceManager(gmxapi.operation.SourceResource):
#
#     def data(self) -> _OutputDataProxyType:
#         pass
#
#     def is_done(self, name: str) -> bool:
#         pass
#
#     def get(self, name: str) -> 'OutputData':
#         pass
#
#     def update_output(self):
#         pass
#
#     def reset(self):
#         pass
#
#     def width(self) -> int:
#         pass


# class _GetItemFuture(gmxapi.operation.Future):
class _GetItemFuture:
    def __init__(self, owner: 'Executable', attr: str, item: str, key: str, width: int = 1):
        self._owner = owner
        self._output_attr = attr
        self._item = item
        self._key = key
        self.description = gmxapi.operation.ResultDescription(dtype=str, width=width)
        # resource_manager=None
        # super().__init__(resource_manager, item, description)


    @property
    def dtype(self) -> type:
        return str

    def result(self):
        output = self._owner.task.output
        attr = getattr(output, self._output_attr)
        item = attr[self._key]
        return item.result()


class Executable:
    _kwargs: dict
    output_file: dict

    def __init__(self):
        self.output_file = dict()
        self._instance = None
        self._width = None

    @property
    def task(self):
        if self._instance is None:
            self._instance = gmxapi.commandline_operation(
                **self._kwargs
            )
        return self._instance

    def run(self):
        # TODO: inputs may need to be localized or substituted.
        return self.task.run()

    def done(self):
        # TODO: inputs may need to be localized or substituted.
        return self.task.done()

    @classmethod
    def create(cls,
               argv: typing.Union[CommandLineArgvType, Sequence[CommandLineArgvType]],
               stdin: Optional[SupportsEnsemble[str]] = None,
               env: Optional[SupportsEnsemble[dict]] = None):
        """Stateful parser from scalems.executable arguments to gmxapi commandline_operation args.

        Allows retention of file placeholder annotations.
        """
        if not isinstance(argv, collections.abc.Sequence) or isinstance(argv, (str, bytes)) or len(argv) == 0:
            raise TypeError(f'argv must be a sequence of command line arguments. Got {type(argv)}.')

        if stdin is not None and not isinstance(stdin, (str, Future)):
            if not isinstance(stdin, collections.abc.Sequence) \
                    or len(stdin) == 0 \
                    or not all(isinstance(element, str) for element in stdin):
                raise TypeError(
                    'If provided, stdin must be a string or (for ensemble input) a sequence of strings.')

        cmd = Executable()

        # Check for ensemble input and parse argv.
        if isinstance(argv[0], collections.abc.Sequence) and not isinstance(argv[0], (str, bytes)):
            # A list of argv sequences is valid ensemble input as long as they have compatible input and
            # output edges.
            kwargs_list = [cmd._parse_argv(element) for element in argv]
            _executable = kwargs_list[0].executable
            if not all(_executable == kwargs.executable for kwargs in kwargs_list):
                # This is a constraint of gmxapi.commandline_operation. It does not necessarily
                # need to be preserved in scalems.executable, but this is a potential discussion point.
                raise ValueError('Ensemble command line operations must use the same command line tool.')
            _arguments = [kwargs.arguments for kwargs in kwargs_list]
            _input_files = [kwargs.input_files for kwargs in kwargs_list]
            _output_files = [kwargs.output_files for kwargs in kwargs_list]
        else:
            kwargs = cmd._parse_argv(argv)
            _executable = kwargs.executable
            _arguments = kwargs.arguments
            _input_files = kwargs.input_files
            _output_files = kwargs.output_files
        cmd._kwargs={
            'executable': _executable,
            'arguments': _arguments,
            'input_files': _input_files,
            'output_files': _output_files,
            'stdin': stdin,
            'env': env
        }
        width = max(len(item) for item in cmd._kwargs.values() if isinstance(item, list))
        for future in cmd.output_file.values():
            future.description._width = width
        return cmd

    def _parse_argv(self, argv: Sequence[typing.Union[str, Future[str], PlaceHolder[str]]]):
        """Process a sequence into positional arguments and I/O flag mappings.

        Bare strings are either positional arguments or input/output flags.

        Input flags are followed by one or more Future arguments, which establish
        data flow dependencies.

        Output flags are followed by one or more placeholders to establish named
        outputs for the task.
        """
        # For gmxapi.commandline_operation, positional arguments must come before input/output
        # file arguments.
        if isinstance(argv, (str, bytes)) or not isinstance(argv, collections.abc.Sequence) or len(argv) == 0:
            raise TypeError('argv must be the array of command line arguments (including the executable).')
        num_args = len(argv)
        executable = str(argv[0])

        if num_args == 1:
            return _ParsedArgs(executable=executable)

        # Gather positional arguments.
        assert num_args > 1
        previous_arg = argv[1]
        if not isinstance(previous_arg, (str, pathlib.Path)):
            raise ValueError(
                'Unsupported command line syntax. Basic strings must be used for positional arguments. '
                'Input and output files must be provided with a "flag" argument for identification.')
        arguments = []
        input_files: typing.Dict[str, typing.Union[Future[str], str]] = {}
        output_files: typing.Dict[str, str] = {}
        flag: Optional[str] = None
        i = 1
        # Scan for input/output flags by looking for non-string flag arguments.
        for i, arg in enumerate(argv[2:], start=2):
            if isinstance(arg, (str, pathlib.Path)):
                arguments.append(str(previous_arg))
                previous_arg = arg
            elif isinstance(arg, (gmxapi.abc.Future, Reference)):
                flag = previous_arg
                if isinstance(arg, gmxapi.abc.Future):
                    input_files[flag] = arg
                else:
                    # What do we need to do to turn this into a gmxapi Future?
                    # input_files[flag] = arg
                    raise MissingImplementationError()
                break
            elif isinstance(arg, OutputFilePlaceholder):
                flag = previous_arg
                output_files[flag] = get_path(arg)
                item = arg.label
                self.output_file[item] = _GetItemFuture(owner=self, attr='file', item=item, key=flag)
                break
            else:
                raise ValueError(f'Invalid element in argv: {repr(arg)}')

        if flag is None:
            # No non-positional arguments found. Handle the final argument and return.
            arguments.append(previous_arg)
            return _ParsedArgs(executable=executable, arguments=arguments)
        else:
            # input/output arguments found. argv[i-1] is a flag and argv[i] was its
            # (first) argument.
            previous_arg = argv[i]

        # Extend the first I/O flag (discovered above), if necessary,
        # and gather any remaining I/O flags and file arguments.
        for arg in argv[i + 1:]:
            if isinstance(arg, str):
                # Check for empty file lists before discarding the previous flag.
                if isinstance(previous_arg, str):
                    assert previous_arg is flag
                    raise ValueError(
                        f'Flags {repr(previous_arg)} and {repr(arg)} appeared in sequence '
                        f'where input/output flags and arguments are expected.')
                # We don't know yet whether it is an input or output flag.
                # We will infer on a later iteration from its argument type.
                flag = arg
                if flag in input_files or flag in output_files:
                    raise ValueError(f'Duplicated input/output file flags not supported: {flag}')
            elif isinstance(arg, OutputFilePlaceholder):
                if flag in input_files:
                    raise ValueError(f'Output file {arg} provided to {flag}, but {flag} is an input file flag.')
                # gmxapi.commandline_operation currently requires one filename per flag.
                # if flag not in output_files:
                #     output_files[flag] = []
                # output_files[flag].append(get_path(arg))
                if flag in output_files:
                    raise ValueError(f'Output file {arg} provided to {flag}, but {flag} is already set to '
                                     f'{output_files[flag]}.')
                else:
                    output_files[flag] = get_path(arg)
                    item = arg.label
                    self.output_file[item] = _GetItemFuture(owner=self, attr='file', item=item, key=flag)
            elif isinstance(arg, gmxapi.abc.Future):
                if flag in output_files:
                    raise ValueError(f'Input file provided to {flag}, but {flag} is an output file flag.')
                # gmxapi.commandline_operation currently requires one filename per flag.
                # if flag not in input_files:
                #     input_files[flag] = []
                # input_files[flag].append(arg)
                if flag in input_files:
                    raise ValueError(f'Input file {arg} provided to {flag}, but {flag} is already set to '
                                     f'{input_files[flag]}.')
                else:
                    input_files[flag] = arg
            else:
                raise ValueError(f'Cannot process input/output file argument {repr(arg)}.')
            previous_arg = arg

        if flag is previous_arg:
            raise ValueError(f'Got flag {flag} with no arguments.')

        return _ParsedArgs(
            executable=executable,
            arguments=arguments,
            input_files=input_files,
            output_files=output_files
        )


def executable(argv: typing.Union[CommandLineArgvType, Sequence[CommandLineArgvType]], *,
               resources: Optional[SupportsEnsemble[dict]] = None,
               inputs: Optional[SupportsEnsemble[Sequence]] = None,
               outputs: Optional[SupportsEnsemble[Sequence]] = None,
               stdin: Optional[SupportsEnsemble[str]] = None,
               env: Optional[SupportsEnsemble[dict]] = None):
    """Wrap a command line executable to produce a Task.

    Arguments:
        argv: command line argument array, beginning with the executable.
        resources: named runtime resource requirements for the executable Task.
        inputs: enumerate implicit inputs (beyond command line arguments).
        outputs: enumerate implicit outputs (beyond *output_file* elements in *argv*).
        stdin: A string (including line breaks) to be sent to the executable.
        env: optionally substitute a given dictionary instead of inheriting
             environment variables from the execution environment or launch method.

    The first element of *argv* is assumed to be the executable. If the first
    element of *argv* is not a Path or a suitable representation of a filesystem
    path, but is a Sequence, *argv* is assumed to describe an array of Tasks.
    Elements of *argv* may be strings (compatible with filesystem encoding),
    Futures, or placeholders (see `output_file()`).

    Returns:
        Task handle, providing one or more Future outputs.

    See also:
        :py:func:`output_file()`

    Notes:
        Initial implementation is a wrapper for
        :py:func:`gmxapi.commandline_operation` which incurs some additional
        limitations.
         * All input and output files must occur as command line options.
         * *resources* is not yet supported.
         * tasks are executed sequentially to avoid resource conflicts.
         * *env* must be overwritten for MPI-aware executables when the script
           is executed as an MPI task (e.g. ``mpiexec ... python -m mpi4py myscript.py``)
    """
    # Initial implementation wraps `gmxapi.commandline_operation`.
    if resources is not None:
        raise MissingImplementationError('resources argument is not yet supported.')
    if inputs is not None:
        # We need to consider what to do when entries in *inputs* duplicate elements of *argv*.
        raise MissingImplementationError('inputs argument is not yet supported.')
    if outputs is not None:
        # We need to consider what to do when entries in *outputs* duplicate elements of *argv*.
        raise MissingImplementationError('outputs argument is not yet supported.')

    cmd = Executable.create(argv=argv, stdin=stdin, env=env)
    return cmd
