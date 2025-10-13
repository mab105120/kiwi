from typing import Dict
from rich.console import Console

_console = Console()

def collect_inputs(variables: Dict[str, str]) -> Dict[str, str]:
    input_vals = {}
    for label, var in variables.items():
        val = _console.input(f"{label}: ")
        input_vals[var] = val
    _console.print("\n")
    return input_vals