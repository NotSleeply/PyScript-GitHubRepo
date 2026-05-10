"""Configuration layer: load YAML defaults, parse CLI flags, merge, validate.

The public entry point remains `parse_and_merge_args()` which returns the
fully-resolved options dict used by the rest of the app.
"""

from src.config.loader import load_config, parse_and_merge_args
from src.config.validator import validate_config

__all__ = ["load_config", "parse_and_merge_args", "validate_config"]
