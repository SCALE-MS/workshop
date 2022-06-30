import dataclasses
import typing
import weakref
from enum import auto as enum_auto
from enum import Enum

import gmxapi

from scalems_workshop._abc import getattr_proxy


class Command(Enum):
    ADD = enum_auto()
    SET = enum_auto()


@dataclasses.dataclass
class Step:
    key: str
    command: Command


@dataclasses.dataclass
class AddStep(Step):
    func: typing.Callable
    args: tuple
    kwargs: dict


@dataclasses.dataclass
class SetStep(Step):
    source: object


class VariableState(Enum):
    EDITING = enum_auto()  # Initial editable state during class definition.
    INITIALIZED = enum_auto()  # Fully initialized after class creation.


class SubgraphVariable:
    """Define a labeled point in Subgraph data flow."""
    _key: str
    _shape: tuple
    _state: VariableState
    _type: type

    def set(self, update):
        ...


@dataclasses.dataclass
class _SubstepVariableReference:
    substep: int
    referent: SubgraphVariable


class _SubgraphVariableEditor(SubgraphVariable):
    """SubgraphVariable in an editable state.


    """
    _substep_value: list

    def __init__(self, default):
        self._type = type(default)
        self._state = VariableState.EDITING
        self._shape = (1,)
        # We pick up the name during Subgraph.__set_name__() once the namespace is populated.
        self._key = ''
        # Variables may be read from or assigned multiple times in arbitrary sequence. When read
        # in the editing state, we need to note which phase we are reading. When setting, we
        # need to increment the substep.
        self._substep_value = [default]

    def set(self, update):
        self._substep_value.append(update)

    def get(self):
        substep = len(self._substep_value) - 1
        assert substep >= 0
        return _SubstepVariableReference(substep=substep, referent=self._substep_value[substep])


class _SubgraphVariableDescriptor(SubgraphVariable):
    """Attribute type for a Subgraph subclass "variable" member."""
    _default_value = None

    def default(self):
        return self._default_value


class _NodeProxy:
    """Represent access into a SubgraphNode that might need to be deferred or translated before execution."""

    def __getattr__(self, item):
        return getattr_proxy(self, item)


@getattr_proxy.register
def _(source: _NodeProxy, item: str):
    proxy = _NodeProxy()
    # Warning: These strong references could be problematic if we don't clean up
    # proxy instances as soon as possible.
    proxy.owner = source
    proxy.attr = item
    return proxy


class SubgraphNode:
    """Describe a subtask within a Subgraph.

    The result of a subgraph add command.
    """

    def __init__(self, func: typing.Callable, args: tuple, kwargs: dict):
        # Record the details of the task supporting the node.
        self.func = func
        self.args = args
        self.kwargs = kwargs
        # We pick up the name during Subgraph.__set_name__() once the namespace is populated.
        self.key = ''

    def __getattr__(self, item):
        # Proxy attribute access to something that can be instantiated during translation to
        # gmxapi.subgraph.
        return getattr_proxy(self, item)


@getattr_proxy.register
def _(source: SubgraphNode, item: str):
    proxy = _NodeProxy()
    # The SubgraphNode will outlive any valid proxy object, but proxy objects may not be
    # de-referenced as early as we would like.
    proxy.owner = weakref.proxy(source)
    proxy.attr = item
    return proxy


def output_variable(default=None):
    return _SubgraphVariableEditor(default=default)


def add(func, *args, **kwargs) -> SubgraphNode:
    return SubgraphNode(func, args, kwargs)


class SubgraphMeta:
    """Metaclass for preparing and processing the namespace of Subgraph subclasses."""


class Subgraph(metaclass=SubgraphMeta):
    """Framework for composing reusable tasks with internal data flow.

    Can be used to generate an arbitrary number of chained tasks,
    e.g. as iterations of a while_loop.
    """


@dataclasses.dataclass
class _ConditionAnnotation:
    source: object
    transformation: str


def logical_not(condition):
    """Annotate *condition* with a logical NOT.

     When `while_loop` transforms *condition* for gmxapi.while_loop, apply
     gmxapi.logical_not().
     """
    return _ConditionAnnotation(source=condition, transformation='logical_not')


def _translate_condition(condition, subgraph):
    if isinstance(condition, _SubgraphVariableDescriptor):
        _condition = ...
        raise RuntimeError('missing implementation!')
    elif isinstance(condition, _ConditionAnnotation):
        if condition.transformation != 'logical_not':
            raise ValueError(f'{condition} not implemented.')
        _condition = gmxapi.logical_not(_translate_condition(condition, subgraph))
    else:
        raise ValueError(f'No handler for condition of this type: {repr(condition)}.')
    return _condition


def while_loop(operation: typing.Type[Subgraph], *, condition, max_iteration=10):
    """Use a Subgraph class definition object to direct the gmxapi subgraph while loop."""
    #     subgraph = gmx.subgraph(
    #         variables={
    #             'found_native': False,
    #             'checkpoint': '',
    #             'min_rms': 1e6
    #         })
    #     with subgraph:
    #         md = gmx.mdrun(
    #             simulation_input,
    #             runtime_args={
    #                 '-cpi': subgraph.checkpoint,
    #                 '-maxh': str(maxh),
    #                 '-noappend': None,
    #                 '-nt': str(threads_per_rank)
    #             })
    #
    #         subgraph.checkpoint = md.output.checkpoint
    #         rmsd = gmx.commandline_operation(
    #             'gmx', ['rms'],
    #             input_files={
    #                 '-s': reference_struct,
    #                 '-f': md.output.trajectory
    #             },
    #             output_files={'-o': 'rmsd.xvg'},
    #             stdin='Backbone Backbone\n'
    #         )
    #         subgraph.min_rms = numeric_min(
    #             xvg_to_array(rmsd.output.file['-o']).output.data).output.data
    #         subgraph.found_native = less_than(lhs=subgraph.min_rms, rhs=0.3).output.data

    if not isinstance(operation, Subgraph):
        raise ValueError('Unsupported *operation* value: {repr(operation)}.')
    variables = {}
    for key in dir(operation):
        attr = getattr(operation, key)
        if isinstance(attr, _SubgraphVariableDescriptor):
            variables[key] = attr.default()
    internal_handles = {}
    _subgraph = gmxapi.subgraph(variables=variables)
    with _subgraph:
        # Apply the sequence of assignments needed.
        for step in operation.dag():
            if step.command == Command.ADD:
                assert isinstance(step, AddStep)
                # TODO: recursively process args and kwargs
                args = step.args
                kwargs = step.kwargs
                internal_handles[step.key] = step.func(*args, **kwargs)
            elif step.command == Command.SET:
                assert isinstance(step, SetStep)
                # TODO: 'source' probably needs some processing.
                setattr(_subgraph, step.key, step.source)
            else:
                raise RuntimeError(f'No processing available for {repr(step)}.')

    _condition = _translate_condition(condition, _subgraph)
    _while_loop = gmxapi.while_loop(operation=_subgraph, condition=_condition, max_iteration=max_iteration)
