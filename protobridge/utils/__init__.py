"""
Utility modules for ProtoBridge.

Includes configuration loader, YAML parser (zero-dependency),
and helper functions.
"""

import json
import os
import re
import sys
from typing import Dict, List, Optional, Any, Union


class YamlParser:
    """Minimal YAML parser using only Python standard library.

    Supports: key-value pairs, nested dicts, lists, strings, numbers,
    booleans, null, multi-line strings, and comments.
    """

    @staticmethod
    def parse(content: str) -> Any:
        """Parse YAML content into Python objects."""
        lines = content.split("\n")
        return YamlParser._parse_lines(lines, 0, 0)[0]

    @staticmethod
    def parse_file(filepath: str) -> Any:
        """Parse a YAML file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return YamlParser.parse(f.read())

    @staticmethod
    def _get_indent(line: str) -> int:
        """Get the indentation level of a line."""
        return len(line) - len(line.lstrip())

    @staticmethod
    def _is_empty_or_comment(line: str) -> bool:
        """Check if line is empty or a comment."""
        stripped = line.strip()
        return not stripped or stripped.startswith("#")

    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Parse a YAML value string into appropriate Python type."""
        stripped = value_str.strip()

        # Handle quoted strings
        if (stripped.startswith('"') and stripped.endswith('"')) or \
           (stripped.startswith("'") and stripped.endswith("'")):
            return stripped[1:-1]

        # Handle multi-line string indicator
        if stripped in ("|", ">"):
            return stripped

        # Handle booleans
        if stripped.lower() in ("true", "yes", "on"):
            return True
        if stripped.lower() in ("false", "no", "off"):
            return False

        # Handle null
        if stripped.lower() in ("null", "none", "~", ""):
            return None

        # Handle numbers
        try:
            if "." in stripped or "e" in stripped.lower():
                return float(stripped)
            if stripped.startswith("0x"):
                return int(stripped, 16)
            if stripped.startswith("0o"):
                return int(stripped, 8)
            return int(stripped)
        except ValueError:
            pass

        # Handle inline lists
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1].strip()
            if inner:
                return [YamlParser._parse_value(item.strip())
                        for item in inner.split(",")]
            return []

        # Handle inline dicts
        if stripped.startswith("{") and stripped.endswith("}"):
            inner = stripped[1:-1].strip()
            if inner:
                result = {}
                for pair in inner.split(","):
                    if ":" in pair:
                        k, v = pair.split(":", 1)
                        result[k.strip()] = YamlParser._parse_value(v.strip())
                return result
            return {}

        return stripped

    @staticmethod
    def _parse_lines(lines: List[str], start: int,
                     base_indent: int) -> tuple:
        """Parse lines at a given indentation level."""
        result: Any = {}
        i = start
        current_list: Optional[List[Any]] = None
        list_indent = -1

        while i < len(lines):
            line = lines[i]

            if YamlParser._is_empty_or_comment(line):
                i += 1
                continue

            indent = YamlParser._get_indent(line)

            if indent < base_indent:
                break

            if indent > base_indent:
                i += 1
                continue

            stripped = line.strip()

            # Handle list items
            if stripped.startswith("- "):
                if current_list is None:
                    current_list = []
                    list_indent = indent
                    # Find the key this list belongs to
                    if isinstance(result, dict) and result:
                        # This shouldn't happen at this level
                        pass
                    else:
                        result = current_list

                item_value = stripped[2:].strip()

                # Check if list item has nested content
                if not item_value and i + 1 < len(lines):
                    next_indent = YamlParser._get_indent(lines[i + 1])
                    if next_indent > indent:
                        nested, i = YamlParser._parse_lines(lines, i + 1, next_indent)
                        current_list.append(nested)
                        continue

                current_list.append(YamlParser._parse_value(item_value))
                i += 1
                continue
            else:
                current_list = None

            # Handle key-value pairs
            if ":" in stripped and not stripped.startswith("-"):
                colon_pos = stripped.index(":")
                key = stripped[:colon_pos].strip()
                value_str = stripped[colon_pos + 1:].strip()

                # Check for nested content on next lines
                if not value_str and i + 1 < len(lines):
                    next_indent = YamlParser._get_indent(lines[i + 1])
                    if next_indent > indent:
                        nested, i = YamlParser._parse_lines(lines, i + 1, next_indent)
                        if isinstance(result, dict):
                            result[key] = nested
                        else:
                            result = {key: nested}
                        continue

                if isinstance(result, dict):
                    result[key] = YamlParser._parse_value(value_str)
                else:
                    result = {key: YamlParser._parse_value(value_str)}

            i += 1

        return result, i


class ConfigLoader:
    """Configuration file loader supporting YAML and JSON formats."""

    @staticmethod
    def load(filepath: str) -> Dict[str, Any]:
        """Load configuration from file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        ext = os.path.splitext(filepath)[1].lower()

        if ext in (".yaml", ".yml"):
            parsed = YamlParser.parse(content)
        elif ext == ".json":
            parsed = json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                parsed = YamlParser.parse(content)
            except Exception:
                parsed = json.loads(content)

        if not isinstance(parsed, dict):
            raise ValueError(f"Configuration root must be a dict, got {type(parsed).__name__}")

        return parsed

    @staticmethod
    def load_env_overrides(config: Dict[str, Any],
                           prefix: str = "PROTOBRIDGE_") -> Dict[str, Any]:
        """Override config values from environment variables."""
        result = dict(config)
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                # Support nested keys with double underscore
                parts = config_key.split("__")
                current = result
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = ConfigLoader._parse_env_value(value)
        return result

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable value."""
        if value.lower() in ("true", "yes", "on"):
            return True
        if value.lower() in ("false", "no", "off"):
            return False
        if value.lower() in ("null", "none"):
            return None
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value


class ColorFormatter:
    """ANSI color formatter for terminal output."""

    COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }

    @staticmethod
    def format(text: str, *colors: str) -> str:
        """Apply colors to text."""
        result = ""
        for color in colors:
            result += ColorFormatter.COLORS.get(color, "")
        result += text
        result += ColorFormatter.COLORS["reset"]
        return result

    @staticmethod
    def strip(text: str) -> str:
        """Remove all ANSI color codes from text."""
        return re.sub(r"\033\[[0-9;]+m", "", text)

    @classmethod
    def supports_color(cls) -> bool:
        """Check if terminal supports colors."""
        if os.environ.get("NO_COLOR"):
            return False
        if not hasattr(sys.stdout, "isatty"):
            return True
        return sys.stdout.isatty()


class TableFormatter:
    """Simple table formatter for terminal output."""

    @staticmethod
    def format(headers: List[str], rows: List[List[str]],
               padding: int = 2) -> str:
        """Format data as an aligned table."""
        if not rows:
            return "  (no data)"

        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Build table
        lines = []
        # Header
        header_line = " " * padding
        for i, h in enumerate(headers):
            header_line += str(h).ljust(col_widths[i]) + " " * padding
        lines.append(header_line)

        # Separator
        sep_line = " " * padding
        for w in col_widths:
            sep_line += "-" * w + " " * padding
        lines.append(sep_line)

        # Rows
        for row in rows:
            row_line = " " * padding
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    row_line += str(cell).ljust(col_widths[i]) + " " * padding
            lines.append(row_line)

        return "\n".join(lines)
