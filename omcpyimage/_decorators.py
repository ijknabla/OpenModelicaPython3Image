from collections.abc import Callable
from contextlib import ExitStack, suppress
from functools import WRAPPER_ASSIGNMENTS, wraps
from typing import Any, ParamSpec, Protocol, Type, TypeGuard, TypeVar, overload

from schema import SchemaError

P = ParamSpec("P")

T_arg0 = TypeVar("T_arg0", contravariant=True)
T_arg1 = TypeVar("T_arg1", contravariant=True)
T_return = TypeVar("T_return", covariant=True)


class SupportsSchema:
    def validate(self, obj: Any) -> None:
        ...


ReturnsSchema = Callable[[], SupportsSchema]


class SupportsCheck(Protocol[T_arg0, T_return]):
    def __call__(self, obj: T_arg0, check: bool = True) -> TypeGuard[T_return]:
        ...


@overload
def schema2checker(
    t_args: Type[T_arg0],
    t_return: Type[T_return],
) -> Callable[[ReturnsSchema], SupportsCheck[T_arg0, T_return]]:
    ...


@overload
def schema2checker(
    t_args: tuple[Type[T_arg0]],
    t_return: Type[T_return],
) -> Callable[[ReturnsSchema], SupportsCheck[T_arg0, T_return]]:
    ...


@overload
def schema2checker(
    t_args: tuple[Type[T_arg0], Type[T_arg1]],
    t_return: Type[T_return],
) -> Callable[[ReturnsSchema], SupportsCheck[T_arg0 | T_arg1, T_return]]:
    ...


@overload
def schema2checker(
    t_args: Any,
    t_return: Type[T_return],
) -> Callable[[ReturnsSchema], SupportsCheck[Any, T_return]]:
    ...


def schema2checker(
    t_args: Type[T_arg0]
    | tuple[Type[T_arg0]]
    | tuple[Type[T_arg0], Type[T_arg1]],
    t_return: Type[T_return],
) -> Callable[[ReturnsSchema], SupportsCheck[T_arg0 | T_arg1, T_return]]:
    def decorator(
        f: ReturnsSchema,
    ) -> SupportsCheck[T_arg0 | T_arg1, T_return]:
        @wraps(
            f,
            assigned=[
                i for i in WRAPPER_ASSIGNMENTS if i not in {"__annotations__"}
            ],
        )
        def wrapped(
            obj: T_arg0 | T_arg1, check: bool = True
        ) -> TypeGuard[T_return]:
            with ExitStack() as stack:
                if not check:
                    stack.enter_context(suppress(SchemaError))
                f().validate(obj)
                return True
            return False

        return wrapped

    return decorator
