"""The guest's half of the tool protocol (spec 031): `from host import tools`.

The embedder offers tools; `host.tools` asks for them when it is first imported and holds one
function per tool. Importing `host` alone sends nothing. A failed call raises one of the classes
below; each `ToolError` names its kind in `.kind`. A cancelled run is stopped by the runner at
its next function entry, so `except ToolCancelled` is no place for clean-up.
"""

PROTOCOL = 1


class ToolError(Exception):
    """A tool call failed (`tool_error`); the base of every class below."""

    kind = "tool_error"


class ToolDenied(ToolError, PermissionError):
    """The embedder's gate or the tool refused the call (`denied`)."""

    kind = "denied"


class ToolArgumentError(ToolError, TypeError):
    """The arguments do not fit the tool, or no tool has that name (`invalid_arguments`,
    `unknown_tool`)."""

    kind = "invalid_arguments"


class ToolTimeout(ToolError, TimeoutError):
    """The tool did not answer in its time (`timeout`)."""

    kind = "timeout"


class ToolCancelled(ToolError):
    """The run was cancelled while the tool ran (`cancelled`)."""

    kind = "cancelled"


class ToolTooLarge(ToolError):
    """The request or the result is over its cap (`too_large`)."""

    kind = "too_large"


class ToolBudgetExceeded(ToolError):
    """This run has used all the tool calls it may make (`budget_exceeded`)."""

    kind = "budget_exceeded"


class ToolProtocolError(ToolError):
    """The frame broke the protocol, the door failed, or the answer did not match (`protocol`)."""

    kind = "protocol"


__all__ = [
    "PROTOCOL",
    "ToolError",
    "ToolDenied",
    "ToolArgumentError",
    "ToolTimeout",
    "ToolCancelled",
    "ToolTooLarge",
    "ToolBudgetExceeded",
    "ToolProtocolError",
]
