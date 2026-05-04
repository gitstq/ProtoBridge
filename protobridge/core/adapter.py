"""
Protocol adapter engine for ProtoBridge.

Handles YAML-based protocol mapping definitions, request/response
transformation pipelines, and route generation from configuration.
"""

import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Tuple

from .server import (
    RequestContext, ResponseContext, Router, BridgeServer
)


class TransformRule:
    """A single transformation rule for request or response data."""

    def __init__(self, rule_type: str, source: str, target: str = "",
                 default: Any = None, transform: Optional[str] = None):
        self.rule_type = rule_type  # "move", "copy", "rename", "remove", "default", "template"
        self.source = source
        self.target = target
        self.default = default
        self.transform = transform  # "upper", "lower", "int", "float", "str", "bool"

    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply this transformation rule to the data dict."""
        if self.rule_type == "move":
            value = self._get_value(data, self.source)
            if value is not None:
                self._remove_value(data, self.source)
                self._set_value(data, self.target, self._apply_transform(value))
        elif self.rule_type == "copy":
            value = self._get_value(data, self.source)
            if value is not None:
                self._set_value(data, self.target, self._apply_transform(value))
        elif self.rule_type == "rename":
            value = self._get_value(data, self.source)
            if value is not None:
                self._remove_value(data, self.source)
                self._set_value(data, self.target, self._apply_transform(value))
        elif self.rule_type == "remove":
            self._remove_value(data, self.source)
        elif self.rule_type == "default":
            value = self._get_value(data, self.source)
            if value is None:
                self._set_value(data, self.source, self.default)
        elif self.rule_type == "template":
            template_str = self._get_value(data, self.source) or self.source
            result = self._render_template(template_str, data)
            self._set_value(data, self.target, result)

        return data

    def _apply_transform(self, value: Any) -> Any:
        """Apply value transformation."""
        if self.transform is None or value is None:
            return value
        try:
            if self.transform == "upper":
                return str(value).upper()
            elif self.transform == "lower":
                return str(value).lower()
            elif self.transform == "int":
                return int(value)
            elif self.transform == "float":
                return float(value)
            elif self.transform == "str":
                return str(value)
            elif self.transform == "bool":
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes", "on")
        except (ValueError, TypeError):
            return value
        return value

    def _get_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def _set_value(self, data: Dict[str, Any], path: str, value: Any):
        """Set nested value in dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _remove_value(self, data: Dict[str, Any], path: str):
        """Remove nested value from dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]

    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Render a template string with variable substitution."""
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_value(data, var_path)
            return str(value) if value is not None else match.group(0)

        return re.sub(r"\{\{(\w+(?:\.\w+)*)\}\}", replace_var, template)


class TransformPipeline:
    """A pipeline of transformation rules applied in sequence."""

    def __init__(self, rules: Optional[List[TransformRule]] = None):
        self.rules: List[TransformRule] = rules or []

    def add_rule(self, rule: TransformRule):
        """Add a transformation rule to the pipeline."""
        self.rules.append(rule)

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all transformation rules on the data."""
        result = dict(data)
        for rule in self.rules:
            result = rule.apply(result)
        return result

    @classmethod
    def from_config(cls, config: List[Dict[str, Any]]) -> "TransformPipeline":
        """Create a pipeline from configuration dict."""
        rules = []
        for rule_cfg in config:
            rule = TransformRule(
                rule_type=rule_cfg.get("type", "move"),
                source=rule_cfg.get("source", ""),
                target=rule_cfg.get("target", ""),
                default=rule_cfg.get("default"),
                transform=rule_cfg.get("transform"),
            )
            rules.append(rule)
        return cls(rules)


class ProtocolAdapter:
    """Adapter that transforms requests between different API protocols."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.source_protocol = config.get("source_protocol", "generic")
        self.target_protocol = config.get("target_protocol", "generic")
        self.request_pipeline = TransformPipeline.from_config(
            config.get("request_transforms", [])
        )
        self.response_pipeline = TransformPipeline.from_config(
            config.get("response_transforms", [])
        )
        self.base_url = config.get("target_base_url", "")
        self.timeout = config.get("timeout", 30)
        self.strip_prefix = config.get("strip_prefix", "")
        self.add_prefix = config.get("add_prefix", "")
        self.default_headers = config.get("default_headers", {})
        self.forward_headers = config.get("forward_headers", [])

    def adapt_request(self, ctx: RequestContext) -> Tuple[str, Dict[str, str], bytes]:
        """Adapt an incoming request to the target protocol format.

        Returns: (target_url, target_headers, target_body)
        """
        # Build target URL
        target_path = ctx.path
        if self.strip_prefix and target_path.startswith(self.strip_prefix):
            target_path = target_path[len(self.strip_prefix):]
        if self.add_prefix:
            target_path = self.add_prefix + target_path

        if ctx.query_params:
            query_str = urllib.parse.urlencode(ctx.query_params)
            target_path = f"{target_path}?{query_str}"

        target_url = f"{self.base_url}{target_path}"

        # Transform request body
        target_body = ctx.body
        if ctx.body and self.request_pipeline.rules:
            try:
                body_data = json.loads(ctx.body.decode("utf-8"))
                body_data = self.request_pipeline.execute(body_data)
                target_body = json.dumps(body_data, ensure_ascii=False).encode("utf-8")
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Build target headers
        target_headers = dict(self.default_headers)
        for header_name in self.forward_headers:
            value = ctx.get_header(header_name)
            if value:
                target_headers[header_name] = value

        # Update content-length if body changed
        if target_body:
            target_headers["content-length"] = str(len(target_body))

        return target_url, target_headers, target_body

    def adapt_response(self, response_body: bytes, status_code: int) -> ResponseContext:
        """Adapt the target response back to the source protocol format."""
        if self.response_pipeline.rules:
            try:
                body_data = json.loads(response_body.decode("utf-8"))
                body_data = self.response_pipeline.execute(body_data)
                adapted_body = json.dumps(body_data, ensure_ascii=False).encode("utf-8")
                return ResponseContext.json(body_data, status_code)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        return ResponseContext(status_code=status_code, body=response_body)

    def proxy_request(self, ctx: RequestContext) -> ResponseContext:
        """Execute a proxied request to the target server."""
        target_url, target_headers, target_body = self.adapt_request(ctx)

        req = urllib.request.Request(
            target_url,
            data=target_body if target_body else None,
            headers=target_headers,
            method=ctx.method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_body = resp.read()
                return self.adapt_response(resp_body, resp.status)
        except urllib.error.HTTPError as e:
            resp_body = e.read()
            return self.adapt_response(resp_body, e.code)
        except urllib.error.URLError as e:
            return ResponseContext.error(f"Upstream connection failed: {str(e)}", 502)
        except Exception as e:
            return ResponseContext.error(f"Proxy error: {str(e)}", 500)


class AdapterRegistry:
    """Registry for managing protocol adapters."""

    def __init__(self):
        self.adapters: Dict[str, ProtocolAdapter] = {}

    def register(self, adapter: ProtocolAdapter):
        """Register a protocol adapter."""
        self.adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[ProtocolAdapter]:
        """Get an adapter by name."""
        return self.adapters.get(name)

    def list_adapters(self) -> List[str]:
        """List all registered adapter names."""
        return list(self.adapters.keys())

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "AdapterRegistry":
        """Create registry from configuration."""
        registry = cls()
        for name, adapter_cfg in config.items():
            adapter = ProtocolAdapter(name, adapter_cfg)
            registry.register(adapter)
        return registry
