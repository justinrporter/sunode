import logging
import types
from types import MethodType
import pydoc
from typing import Callable, List, Optional, Type, Dict
from typing_extensions import Protocol
import abc

from .problem import OdeProblem


logger = logging.getLogger("pysundials_cffi.builder")


class BuilderOption(Protocol):
    def __init__(self, builder: Builder) -> None:
        ...

    def build(self) -> None:
        ...

    def __call__(self, *args, **kwargs) -> Builder:
        ...

    @property
    def name(self) -> str:
        ...


class Builder:
    _all_options: Dict[str, Type[BuilderOption]] = {}

    @classmethod
    def _option(cls, option_class):
        name = option_class.__name__
        option_class.__call__.__name__ = name
        _all_options[name] = option_class

    def __init__(
        self, problem: OdeProblem, options: List[BuilderOption], required: List[str]
    ) -> None:
        self._options = {opt.name: opt for opt in options}
        self._problem = problem

        self._required = required
        req = set(required)
        self._optional = [option for option in self._options if option not in req]

        self.__doc__ = self._make_docstring(subset="all")

    def help(self, subset: str = "possible") -> None:
        print(self._make_docstring(subset=subset))

    def _make_docstring(self, subset: str = "all") -> str:
        if subset == "all":
            methods = "\n".join(
                pydoc.plaintext.document(option.__call__)
                for option in self._all_options.values()
            )
            return pydoc.plaintext.section("All possible options", methods)
        elif subset == "possible":
            sections = []
            if self._required:
                sec = "\n".join(
                    pydoc.plaintext.document(self._options[opt].__class__.__call__)
                    for opt in self._required
                )
                sec = pydoc.plaintext.section("Required options", sec)
                sections.append(sec)
            if self._optional:
                sec = "\n".join(
                    pydoc.plaintext.document(self._options[opt].__class__.__call__)
                    for opt in self._optional
                )
                sec = pydoc.plaintext.section("Optional options", sec)
                sections.append(sec)
            return "\n".join(sections)
        raise ValueError(
            'Invalid subset: %s. Must be one of "all" or "possible"' % subset
        )

    def _modify(self, remove=None, required=None, optional=None):
        if remove is not None:
            for name in remove:
                required_names = [f.__name__ for f in self._required]
                optional_names = [f.__name__ for f in self._optional]
                if name in required_names:
                    self._required.pop(required_names.index(name))
                elif name in optional_names:
                    self._optional.pop(optional_names.index(name))
                else:
                    raise ValueError("Unknown function %s" % name)
                delattr(self, name)

        if required is not None:
            for func in required:
                bind(self, func)
            req = required.copy()
            req.extend(self._required)
            self._required = req

        if optional is not None:
            for func in optional:
                bind(self, func)
            opt = optional.copy()
            opt.extend(self._optional)
            self._optional = opt

        self.__doc__ = self._make_docstring()
        return self

    # We tell mypy that there are dynamic methods
    def __getattr__(self, name: str) -> BuilderOption:
        raise AttributeError()