"""
ProtoBridge - Lightweight Universal Protocol Adaptation & API Transformation Engine

A zero-dependency Python CLI tool for protocol adaptation, request/response
transformation, and API gateway management via YAML configuration.

Zero external dependencies - uses only Python standard library.
Compatible with Python 3.8+.
"""

from .core.server import (
    BridgeServer, RequestContext, ResponseContext, Router, Route
)
from .core.adapter import (
    ProtocolAdapter, AdapterRegistry, TransformRule, TransformPipeline
)
from .converters import (
    JsonConverter, XmlConverter, FormConverter, HeaderMapper
)
from .middleware import (
    CorsMiddleware, RateLimitMiddleware, LoggingMiddleware,
    CacheMiddleware, AuthMiddleware, RetryMiddleware
)
from .utils import ConfigLoader, YamlParser, ColorFormatter, TableFormatter

__all__ = [
    # Core
    "BridgeServer", "RequestContext", "ResponseContext", "Router", "Route",
    # Adapter
    "ProtocolAdapter", "AdapterRegistry", "TransformRule", "TransformPipeline",
    # Converters
    "JsonConverter", "XmlConverter", "FormConverter", "HeaderMapper",
    # Middleware
    "CorsMiddleware", "RateLimitMiddleware", "LoggingMiddleware",
    "CacheMiddleware", "AuthMiddleware", "RetryMiddleware",
    # Utils
    "ConfigLoader", "YamlParser", "ColorFormatter", "TableFormatter",
]

__version__ = "1.0.0"
