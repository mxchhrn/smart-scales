import importlib.util
import shutil
import pathlib

class ToolNotFoundError(Exception):
    """Raised when a required tool cannot be found in pip or ext/."""
    pass

def locate_tool(name: str, ext_subdir: str = "esp-idf") -> str:
    """
    Locate an ESP-IDF related tool.
    
    - First checks if it's available as a pip module.
    - Then searches in ext/<ext_subdir>/ for the script.
    - Returns the absolute path to the script (or module name if pip-installed).
    - Raises ToolNotFoundError if not found.
    
    Parameters
    ----------
    name : str
        Tool identifier, e.g. "nvs_partition_gen", "gen_esp32part", "espcoredump".
    ext_subdir : str
        Which ext/ subfolder to search in. Defaults to "esp-idf-tools".
    """
    
    # 1. Try pip-installed module (import check)
    if importlib.util.find_spec(name) is not None:
        return name   # Can be run directly with `python -m <name>`
    
    # 2. Try if it's an installed CLI script (pip entrypoint)
    if shutil.which(name):
        return shutil.which(name)
    
    # 3. Search in ext/ folder for .py script
    base = pathlib.Path(__file__).resolve().parents[2] / "ext" / ext_subdir
    candidate = base / f"{name}.py"
    if candidate.exists():
        return str(candidate)
    
    # 4. Not found → raise error
    raise ToolNotFoundError(
        f"Tool '{name}' not found. "
        f"Tried pip module, system PATH, and ext/{ext_subdir}/."
    )
