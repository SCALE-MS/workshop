"""Define the basic interfaces in the package."""
import functools
import typing
from typing import Protocol
from typing import Sequence
from typing import Union

ResultType = typing.TypeVar('ResultType')


class Future(Protocol[ResultType]):
    """Defines the interface of a Task output handle."""

    def result(self) -> ResultType:
        ...


T = typing.TypeVar('T')
TaskInput = Union[Future[T], T]
SupportsEnsemble = Union[TaskInput[T], Sequence[TaskInput[T]]]


class PlaceHolder(typing.Generic[T]):
    """Annotation type allowing for additional processing by the framework."""


@functools.singledispatch
def getattr_proxy(source, item: str) -> 'Reference':
    # Proxy attribute access to something that can be instantiated during translation to
    # gmxapi.subgraph.
    raise ValueError(f'No dispatching for *source* value {repr(source)}.')


class Reference:
    """Reference to an object or operation at a specific point in the data flow."""
    key: str

    referent: typing.Any

    def run(self):
        return self.referent.run()

    def result(self):
        return self.result()

    def __getattr__(self, item):
        # Proxy attribute access to something that can be instantiated during translation to
        # gmxapi.subgraph.
        return getattr_proxy(self, item)


@getattr_proxy.register
def _(source: Reference, item: str):
    proxy = Reference()
    # Warning: These strong references could be problematic if we don't clean up
    # proxy instances as soon as possible.
    proxy.owner = source
    proxy.attr = item
    return proxy
