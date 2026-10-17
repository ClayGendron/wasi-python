# What Pydantic AI derives from a function, with approval required. Run: uv run --isolated --no-project --with pydantic-ai-slim==2.57.0 python -I pydantic_ai_probe.py
import json
from pydantic_ai import Tool, ModelRetry
def get_weather(city: str, units: str = "c") -> dict:
    """Get current weather.

    Args:
        city: City name.
        units: 'c' or 'f'.
    """
    return {}
t = Tool(get_weather, requires_approval=True)
td = t.tool_def
print(json.dumps({"name": td.name, "description": td.description, "kind": td.kind, "params": td.parameters_json_schema}, indent=1))
import pydantic_ai; print(pydantic_ai.__version__ if hasattr(pydantic_ai,'__version__') else '')
