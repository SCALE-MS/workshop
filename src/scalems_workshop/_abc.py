"""Define the basic interfaces in the package."""
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
