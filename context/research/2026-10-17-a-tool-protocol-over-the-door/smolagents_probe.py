# What smolagents derives from a decorated function. Run: uv run --isolated --no-project --with smolagents==1.26.0 python -I smolagents_probe.py
from smolagents import tool
import smolagents
@tool
def get_weather(city: str, units: str = "c") -> dict:
    """Get current weather.

    Args:
        city: City name.
        units: 'c' or 'f'.
    """
    return {"city": city}
print(get_weather.inputs, get_weather.output_type)
print(get_weather.to_code_prompt())
print(smolagents.__version__)
