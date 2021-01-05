from __future__ import annotations

from asyncio.coroutines import iscoroutinefunction
from os import linesep
from typing import (
    Any,
    Awaitable,
    Callable,
    Generic,
    MutableMapping,
    MutableSequence,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from pynvim import Nvim

from .atomic import Atomic
from .lib import async_call
from .logging import log

T = TypeVar("T")

RpcMsg = Tuple[str, Sequence[Any]]


class RpcCallable(Generic[T]):
    def __init__(
        self,
        name: str,
        blocking: bool,
        handler: Union[Callable[..., T], Callable[..., Awaitable[T]]],
    ) -> None:
        self.is_async = iscoroutinefunction(handler)
        if self.is_async and blocking:
            raise ValueError()
        else:
            self.name = name
            self.is_blocking = blocking
            self._handler = handler

    def __call__(self, nvim: Nvim, *args: Any, **kwargs: Any) -> Union[T, Awaitable[T]]:
        if self.is_async:
            aw = cast(Awaitable[T], self._handler(nvim, *args, **kwargs))
            return aw
        elif self.is_blocking:
            return cast(T, self._handler(nvim, *args, **kwargs))
        else:
            handler = cast(Callable[[Nvim, Any], T], self._handler)
            aw = async_call(nvim, handler, nvim, *args, **kwargs)
            return aw


RpcSpec = Tuple[str, RpcCallable[T]]


def _new_lua_func(chan: int, handler: RpcCallable[T]) -> str:
    op = "request" if handler.is_blocking else "notify"
    invoke = f"return vim.rpc{op}({chan}, '{handler.name}', {{...}})"
    return f"{handler.name} = function (...) {invoke} end"


def _new_viml_func(handler: RpcCallable[T]) -> str:
    head = f"function! {handler.name}(...)"
    body = f"  call v:lua.{handler.name}(a:000)"
    tail = f"endfunction"
    return linesep.join((head, body, tail))


def _name_gen(fn: Callable[..., T]) -> str:
    return f"{fn.__module__}.{fn.__qualname__}".replace(".", "_").capitalize()


class RPC:
    def __init__(self, name_gen: Callable[[Callable[..., T]], str] = _name_gen) -> None:
        self._handlers: MutableMapping[str, RpcCallable[Any]] = {}
        self._name_gen = name_gen

    def __call__(
        self,
        blocking: bool,
        name: Optional[str] = None,
    ) -> Callable[[Callable[..., T]], RpcCallable[T]]:
        def decor(handler: Callable[..., T]) -> RpcCallable[T]:
            c_name = name if name else self._name_gen(handler)

            wraped = RpcCallable(name=c_name, blocking=blocking, handler=handler)
            self._handlers[wraped.name] = wraped
            return wraped

        return decor

    def drain(self, chan: int) -> Tuple[Atomic, Sequence[RpcSpec]]:
        atomic = Atomic()
        specs: MutableSequence[RpcSpec] = []
        while self._handlers:
            name, handler = self._handlers.popitem()
            atomic.exec_lua(_new_lua_func(chan, handler=handler), ())
            atomic.exec(_new_viml_func(handler=handler), False)
            specs.append((name, handler))

        return atomic, specs


def nil_handler(name: str) -> RpcCallable:
    def handler(nvim: Nvim, *args: Any) -> None:
        log.warn("MISSING RPC HANDLER FOR: %s - %s", name, args)

    return RpcCallable(name=name, blocking=True, handler=handler)
