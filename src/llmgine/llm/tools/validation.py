from __future__ import annotations

import json
from enum import Enum
from typing import Any, get_args, get_origin, Union

from .exceptions import ToolValidationError


def _is_none_type(t: Any) -> bool:
    return t is type(None)  # noqa


def _coerce_basic(value: Any, target: Any) -> Any:
    if target is str:
        return str(value)
    if target is int:
        if isinstance(value, bool):
            return int(value)
        return int(value)
    if target is float:
        return float(value)
    if target is bool:
        if isinstance(value, str):
            if value.lower() in {"1", "true", "yes", "y", "t"}:
                return True
            if value.lower() in {"0", "false", "no", "n", "f"}:
                return False
        return bool(value)
    return value


def _maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def coerce_value(value: Any, annotation: Any) -> Any:
    """
    Best-effort coercion of 'value' to 'annotation' (PEP 484 / typing constructs).
    Tolerant: raises ToolValidationError only when constraints are explicit & violated.
    """
    if annotation is Any or annotation is None:
        return value

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Union / Optional
    if origin is Union:
        # Try all non-None options
        last_exc: Exception | None = None
        for opt in args:
            if _is_none_type(opt):
                if value is None:
                    return None
                continue
            try:
                return coerce_value(value, opt)
            except Exception as e:
                last_exc = e
                continue
        if value is None:
            return None
        if last_exc:
            raise last_exc
        return value

    # Literals
    if origin is not None and origin.__name__ == "Literal":
        allowed = set(args)
        if value not in allowed:
            raise ToolValidationError(f"Value {value!r} not in allowed set {allowed}")
        return value

    # List / Dict generics
    if origin is list:
        value = _maybe_json(value)
        if not isinstance(value, list):
            raise ToolValidationError("Expected list")
        if args:
            subtype = args[0]
            return [coerce_value(v, subtype) for v in value]
        return value

    if origin is dict:
        value = _maybe_json(value)
        if not isinstance(value, dict):
            raise ToolValidationError("Expected dict")
        # If key/value types provided, coerce values (keys usually str)
        if len(args) == 2:
            k_t, v_t = args
            return {coerce_value(k, k_t): coerce_value(v, v_t) for k, v in value.items()}
        return value

    # Enum
    try:
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            if isinstance(value, annotation):
                return value
            # Accept name or value
            for member in annotation:  # type: ignore
                if value == member.value or value == member.name:
                    return member
            raise ToolValidationError(
                f"Invalid enum value {value!r}; expected one of {[m.value for m in annotation]}"
            )
    except TypeError:
        pass

    # Basic scalars
    if annotation in (str, int, float, bool):
        return _coerce_basic(value, annotation)

    # Fallback: return original
    return value