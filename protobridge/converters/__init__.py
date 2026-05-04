"""
Built-in data converters for ProtoBridge.

Provides common data format conversions: JSON Schema transformation,
XML <-> JSON, Form <-> JSON, Header mapping, etc.
"""

import json
import re
import urllib.parse
from typing import Dict, List, Optional, Any
from xml.etree.ElementTree import Element, tostring, fromstring


class JsonConverter:
    """JSON data transformation utilities."""

    @staticmethod
    def flatten(data: Dict[str, Any], separator: str = ".",
                prefix: str = "") -> Dict[str, Any]:
        """Flatten a nested JSON object into dot-notation keys."""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}{separator}{key}" if prefix else key
            if isinstance(value, dict):
                result.update(JsonConverter.flatten(value, separator, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        result.update(JsonConverter.flatten(
                            item, separator, f"{full_key}[{i}]"
                        ))
                    else:
                        result[f"{full_key}[{i}]"] = item
            else:
                result[full_key] = value
        return result

    @staticmethod
    def unflatten(data: Dict[str, Any], separator: str = ".") -> Dict[str, Any]:
        """Unflatten dot-notation keys into nested JSON object."""
        result: Dict[str, Any] = {}
        for key, value in data.items():
            parts = re.split(r"\.|\[(\d+)\]", key)
            parts = [p for p in parts if p]
            current = result
            for i, part in enumerate(parts[:-1]):
                next_part = parts[i + 1]
                if next_part.isdigit():
                    if part not in current:
                        current[part] = []
                    if isinstance(current[part], list):
                        idx = int(next_part)
                        while len(current[part]) <= idx:
                            current[part].append({})
                        if i + 2 < len(parts):
                            current = current[part][idx]
                        else:
                            current[part][idx] = value
                    continue
                if part not in current:
                    current[part] = {}
                current = current[part]
            if parts:
                last = parts[-1]
                if last.isdigit() and isinstance(current, list):
                    idx = int(last)
                    while len(current) <= idx:
                        current.append(None)
                    current[idx] = value
                else:
                    current[last] = value
        return result

    @staticmethod
    def remap(data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        """Remap keys in a JSON object according to mapping."""
        result = {}
        for old_key, new_key in mapping.items():
            if old_key in data:
                result[new_key] = data[old_key]
        # Keep unmapped keys
        for key, value in data.items():
            if key not in mapping:
                result[key] = value
        return result

    @staticmethod
    def filter_keys(data: Dict[str, Any], keys: List[str],
                    exclude: bool = False) -> Dict[str, Any]:
        """Filter JSON object by keys."""
        if exclude:
            return {k: v for k, v in data.items() if k not in keys}
        return {k: v for k, v in data.items() if k in keys}

    @staticmethod
    def merge(*dicts: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge multiple dictionaries."""
        result: Dict[str, Any] = {}
        for d in dicts:
            for key, value in d.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = JsonConverter.merge(result[key], value)
                else:
                    result[key] = value
        return result


class XmlConverter:
    """XML <-> JSON conversion utilities."""

    @staticmethod
    def xml_to_dict(element: Element) -> Any:
        """Convert XML element to Python dict."""
        result: Dict[str, Any] = {}

        # Handle attributes
        if element.attrib:
            result["@attributes"] = dict(element.attrib)

        # Handle children
        children = list(element)
        if children:
            child_dict: Dict[str, Any] = {}
            for child in children:
                child_data = XmlConverter.xml_to_dict(child)
                if child.tag in child_dict:
                    if not isinstance(child_dict[child.tag], list):
                        child_dict[child.tag] = [child_dict[child.tag]]
                    child_dict[child.tag].append(child_data)
                else:
                    child_dict[child.tag] = child_data
            result.update(child_dict)
        elif element.text and element.text.strip():
            text = element.text.strip()
            # Try to parse as number or boolean
            if result:  # Has attributes
                result["#text"] = text
            else:
                try:
                    return int(text)
                except ValueError:
                    try:
                        return float(text)
                    except ValueError:
                        if text.lower() in ("true", "false"):
                            return text.lower() == "true"
                        return text

        return result if result else ""

    @staticmethod
    def to_json(xml_string: str) -> Dict[str, Any]:
        """Convert XML string to JSON dict."""
        root = fromstring(xml_string)
        return {root.tag: XmlConverter.xml_to_dict(root)}

    @staticmethod
    def dict_to_xml(data: Any, root_tag: str = "root") -> Element:
        """Convert Python dict to XML element."""
        root = Element(root_tag)
        XmlConverter._build_xml(root, data)
        return root

    @staticmethod
    def _build_xml(parent: Element, data: Any):
        """Recursively build XML from dict."""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "@attributes":
                    for attr_key, attr_value in value.items():
                        parent.set(attr_key, str(attr_value))
                elif key == "#text":
                    parent.text = str(value)
                elif isinstance(value, list):
                    for item in value:
                        child = Element(key)
                        XmlConverter._build_xml(child, item)
                        parent.append(child)
                elif isinstance(value, dict):
                    child = Element(key)
                    XmlConverter._build_xml(child, value)
                    parent.append(child)
                else:
                    child = Element(key)
                    child.text = str(value)
                    parent.append(child)
        else:
            parent.text = str(data)

    @staticmethod
    def to_xml(data: Dict[str, Any], root_tag: str = "root",
               encoding: str = "unicode") -> str:
        """Convert dict to XML string."""
        root = XmlConverter.dict_to_xml(data, root_tag)
        return tostring(root, encoding=encoding)

    @staticmethod
    def json_to_xml_string(json_data: Dict[str, Any],
                           root_tag: str = "root") -> str:
        """Convert JSON dict to XML string."""
        root = XmlConverter.dict_to_xml(json_data, root_tag)
        return tostring(root, encoding="unicode")


class FormConverter:
    """Form data <-> JSON conversion utilities."""

    @staticmethod
    def form_to_json(form_string: str) -> Dict[str, Any]:
        """Convert URL-encoded form data to JSON dict."""
        params = urllib.parse.parse_qsl(form_string, keep_blank_values=True)
        result: Dict[str, Any] = {}
        for key, value in params:
            # Handle array notation: key[], key[0]
            base_key = re.sub(r"\[\d*\]$", "", key)
            if base_key != key:
                if base_key not in result:
                    result[base_key] = []
                result[base_key].append(value)
            elif key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                # Try to parse value types
                result[key] = FormConverter._parse_value(value)
        return result

    @staticmethod
    def json_to_form(data: Dict[str, Any]) -> str:
        """Convert JSON dict to URL-encoded form string."""
        params = []
        FormConverter._flatten_for_form(data, "", params)
        return "&".join(params)

    @staticmethod
    def _flatten_for_form(data: Any, prefix: str, params: List[str]):
        """Recursively flatten dict for form encoding."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_prefix = f"{prefix}[{key}]" if prefix else key
                FormConverter._flatten_for_form(value, new_prefix, params)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                new_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"
                FormConverter._flatten_for_form(value, new_prefix, params)
        else:
            params.append(f"{urllib.parse.quote(str(prefix))}={urllib.parse.quote(str(data))}")

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Try to parse a string value into appropriate type."""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
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


class HeaderMapper:
    """HTTP header mapping and transformation utilities."""

    @staticmethod
    def map_headers(headers: Dict[str, str],
                    mapping: Dict[str, str]) -> Dict[str, str]:
        """Map header names according to mapping."""
        result = {}
        for key, value in headers.items():
            new_key = mapping.get(key, mapping.get(key.lower(), key))
            result[new_key] = value
        return result

    @staticmethod
    def add_headers(headers: Dict[str, str],
                    additions: Dict[str, str]) -> Dict[str, str]:
        """Add new headers to existing headers."""
        result = dict(headers)
        result.update(additions)
        return result

    @staticmethod
    def remove_headers(headers: Dict[str, str],
                       remove_keys: List[str]) -> Dict[str, str]:
        """Remove specified headers."""
        remove_lower = {k.lower() for k in remove_keys}
        return {k: v for k, v in headers.items() if k.lower() not in remove_lower}

    @staticmethod
    def rename_content_type(headers: Dict[str, str],
                            from_type: str, to_type: str) -> Dict[str, str]:
        """Rename content-type if it matches from_type."""
        result = dict(headers)
        ct = result.get("content-type", "")
        if from_type.lower() in ct.lower():
            result["content-type"] = to_type
        return result
