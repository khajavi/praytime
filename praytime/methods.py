"""Calculation-method resolution helpers (specs.md §4.2, §10.15).

Implements the ``defaults``-then-method merge used by ``PrayTime.method`` and a
copying accessor for the module method table:

* :func:`resolve_method` — merge ``methods['defaults']`` with the named method's
  overrides, returning a new ``dict`` (an unknown name applies only defaults);
* :func:`get_methods` — a deep copy of :data:`constants.METHODS`.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Mapping

from . import constants as C


def resolve_method(methods: Mapping[str, Mapping[str, Any]], name: str) -> Dict[str, Any]:
    """Resolve the effective calculation parameters for ``name`` (specs.md §4.2).

    Mirrors JS ``this.set(this.methods.defaults).set(this.methods[method])``:
    the ``defaults`` entry is applied first and then overridden by the named
    method. A missing ``name`` (or missing ``defaults``) applies only what is
    present — no exception, matching ``Object.assign(settings, undefined)``
    (specs.md §10.15). The result is always a new ``dict``.
    """
    resolved: Dict[str, Any] = dict(methods.get("defaults", {}))
    override = methods.get(name)
    if override:
        resolved.update(override)
    return resolved


def get_methods() -> Dict[str, Any]:
    """Return a deep copy of :data:`constants.METHODS`.

    Mutating the result (e.g. adding a custom method) never affects the shared
    table or other callers.
    """
    return copy.deepcopy(C.METHODS)
