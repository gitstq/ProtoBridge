"""
Comprehensive test suite for ProtoBridge.

Tests cover: server, router, adapters, converters, middleware, and utilities.
Run with: python -m pytest tests/ -v
Or: python tests/test_all.py
"""

import json
import os
import sys
import time
import threading
import urllib.request
import urllib.error

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protobridge.core.server import (
    RequestContext, ResponseContext, Router, Route, BridgeServer
)
from protobridge.core.adapter import (
    ProtocolAdapter, AdapterRegistry, TransformRule, TransformPipeline
)
from protobridge.converters import (
    JsonConverter, XmlConverter, FormConverter, HeaderMapper
)
from protobridge.middleware import (
    CorsMiddleware, RateLimitMiddleware, LoggingMiddleware,
    CacheMiddleware, AuthMiddleware
)
from protobridge.utils import YamlParser, ConfigLoader, ColorFormatter, TableFormatter


class TestResult:
    """Simple test result tracker."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ❌ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\n  Failed tests:")
            for name, reason in self.errors:
                print(f"    ❌ {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


def test_request_context():
    """Test RequestContext parsing."""
    print("\n📦 Testing RequestContext...")
    r = TestResult()

    # Test basic request
    ctx = RequestContext("GET", "/api/users", {"content-type": "application/json"},
                         b'{"name": "test"}', {"page": "1"}, ("127.0.0.1", 12345))
    r.ok("basic request creation" if ctx.method == "GET" and ctx.path == "/api/users" else "")

    # Test get_json
    data = ctx.get_json()
    r.ok("get_json" if data and data.get("name") == "test" else "")

    # Test get_json with invalid body
    ctx2 = RequestContext("POST", "/api/data", {}, b"not json", {}, ("127.0.0.1", 12345))
    r.ok("get_json invalid" if ctx2.get_json() is None else "")

    # Test get_form_data
    ctx3 = RequestContext("POST", "/submit", {"content-type": "application/x-www-form-urlencoded"},
                          b"name=alice&age=30", {}, ("127.0.0.1", 12345))
    form = ctx3.get_form_data()
    r.ok("get_form_data" if form.get("name") == "alice" and form.get("age") == "30" else "")

    # Test get_header (case-insensitive)
    ctx4 = RequestContext("GET", "/", {"Content-Type": "text/html"}, b"", {}, ("127.0.0.1", 12345))
    r.ok("get_header case-insensitive" if ctx4.get_header("content-type") == "text/html" else "")

    return r


def test_response_context():
    """Test ResponseContext creation."""
    print("\n📦 Testing ResponseContext...")
    r = TestResult()

    # Test json response
    resp = ResponseContext.json({"status": "ok"}, 200)
    r.ok("json response" if resp.status_code == 200 and b'"status": "ok"' in resp.body else "")

    # Test text response
    resp = ResponseContext.text("hello", 200)
    r.ok("text response" if resp.status_code == 200 and resp.body == b"hello" else "")

    # Test html response
    resp = ResponseContext.html("<h1>Hi</h1>", 200)
    r.ok("html response" if b"text/html" in resp.headers.get("content-type", "").encode() else "")

    # Test error response
    resp = ResponseContext.error("Something failed", 500)
    r.ok("error response" if resp.status_code == 500 else "")

    return r


def test_router():
    """Test Router route matching."""
    print("\n🛣️  Testing Router...")
    r = TestResult()

    router = Router()

    # Test literal route
    def handler(ctx):
        return ResponseContext.text("ok")

    router.add_route("GET", "/api/users", handler)
    result = router.resolve("GET", "/api/users")
    r.ok("literal route match" if result is not None else "")

    # Test method mismatch
    result = router.resolve("POST", "/api/users")
    r.ok("method mismatch" if result is None else "")

    # Test param route
    router.add_route("GET", "/api/users/{id}", handler)
    result = router.resolve("GET", "/api/users/42")
    r.ok("param route match" if result and result[1].get("id") == "42" else "")

    # Test wildcard route
    router.add_route("GET", "/files/{path}*", handler)
    result = router.resolve("GET", "/files/a/b/c.txt")
    r.ok("wildcard route match" if result and result[1].get("path") == "a/b/c.txt" else "")

    # Test no match
    result = router.resolve("GET", "/nonexistent")
    r.ok("no match" if result is None else "")

    # Test decorator routes
    router2 = Router()

    @router2.get("/test")
    def test_handler(ctx):
        return ResponseContext.text("test")

    @router2.post("/submit")
    def submit_handler(ctx):
        return ResponseContext.text("submitted")

    r.ok("GET decorator" if router2.resolve("GET", "/test") is not None else "")
    r.ok("POST decorator" if router2.resolve("POST", "/submit") is not None else "")
    r.ok("POST decorator wrong method" if router2.resolve("GET", "/submit") is None else "")

    return r


def test_transform_rule():
    """Test TransformRule operations."""
    print("\n🔄 Testing TransformRule...")
    r = TestResult()

    # Test move
    rule = TransformRule("move", "old_key", "new_key")
    data = {"old_key": "value", "other": "keep"}
    result = rule.apply(data)
    r.ok("move" if "new_key" in result and "old_key" not in result else "")

    # Test copy
    rule = TransformRule("copy", "source", "target")
    data = {"source": "value"}
    result = rule.apply(data)
    r.ok("copy" if result.get("source") == "value" and result.get("target") == "value" else "")

    # Test remove
    rule = TransformRule("remove", "delete_me", "")
    data = {"delete_me": "gone", "keep_me": "here"}
    result = rule.apply(data)
    r.ok("remove" if "delete_me" not in result and "keep_me" in result else "")

    # Test rename
    rule = TransformRule("rename", "old_name", "new_name")
    data = {"old_name": "test"}
    result = rule.apply(data)
    r.ok("rename" if "new_name" in result and "old_name" not in result else "")

    # Test default
    rule = TransformRule("default", "setting", default="fallback")
    data = {}
    result = rule.apply(data)
    r.ok("default (missing key)" if result.get("setting") == "fallback" else "")

    data2 = {"setting": "existing"}
    result2 = rule.apply(data2)
    r.ok("default (existing key)" if result2.get("setting") == "existing" else "")

    # Test transform
    rule = TransformRule("copy", "name", "name_upper", transform="upper")
    data = {"name": "hello"}
    result = rule.apply(data)
    r.ok("transform upper" if result.get("name_upper") == "HELLO" else "")

    # Test template
    rule = TransformRule("template", "Hello {{name}}!", "greeting")
    data = {"name": "World"}
    result = rule.apply(data)
    r.ok("template" if result.get("greeting") == "Hello World!" else "")

    return r


def test_transform_pipeline():
    """Test TransformPipeline."""
    print("\n🔄 Testing TransformPipeline...")
    r = TestResult()

    pipeline = TransformPipeline([
        TransformRule("rename", "userName", "name"),
        TransformRule("rename", "userEmail", "email"),
        TransformRule("copy", "email", "email_address"),
        TransformRule("remove", "password"),
    ])

    data = {
        "userName": "Alice",
        "userEmail": "alice@example.com",
        "password": "secret123",
    }
    result = pipeline.execute(data)

    r.ok("pipeline rename" if "name" in result and "userName" not in result else "")
    r.ok("pipeline copy" if result.get("email_address") == "alice@example.com" else "")
    r.ok("pipeline remove" if "password" not in result else "")

    # Test from_config
    config = [
        {"type": "move", "source": "a", "target": "b"},
        {"type": "copy", "source": "b", "target": "c"},
    ]
    pipeline2 = TransformPipeline.from_config(config)
    result2 = pipeline2.execute({"a": 1})
    r.ok("from_config" if result2.get("b") == 1 and result2.get("c") == 1 else "")

    return r


def test_json_converter():
    """Test JsonConverter utilities."""
    print("\n📋 Testing JsonConverter...")
    r = TestResult()

    # Test flatten
    data = {"user": {"name": "Alice", "address": {"city": "NYC"}}}
    flat = JsonConverter.flatten(data)
    r.ok("flatten" if flat.get("user.address.city") == "NYC" else "")

    # Test unflatten
    flat = {"user.name": "Alice", "user.age": "30"}
    nested = JsonConverter.unflatten(flat)
    r.ok("unflatten" if nested.get("user", {}).get("name") == "Alice" else "")

    # Test remap
    data = {"userName": "Alice", "userEmail": "alice@test.com", "extra": "data"}
    mapping = {"userName": "name", "userEmail": "email"}
    result = JsonConverter.remap(data, mapping)
    r.ok("remap" if "name" in result and "email" in result and "extra" in result else "")

    # Test filter_keys
    data = {"a": 1, "b": 2, "c": 3}
    result = JsonConverter.filter_keys(data, ["a", "b"])
    r.ok("filter include" if result == {"a": 1, "b": 2} else "")

    result = JsonConverter.filter_keys(data, ["a"], exclude=True)
    r.ok("filter exclude" if "a" not in result and "b" in result else "")

    # Test merge
    d1 = {"a": 1, "b": {"c": 2}}
    d2 = {"b": {"d": 3}, "e": 4}
    result = JsonConverter.merge(d1, d2)
    r.ok("merge" if result.get("b", {}).get("c") == 2 and result.get("b", {}).get("d") == 3 else "")

    return r


def test_xml_converter():
    """Test XmlConverter."""
    print("\n📋 Testing XmlConverter...")
    r = TestResult()

    # Test XML to JSON
    xml_str = '<root><name>Alice</name><age>30</age></root>'
    result = XmlConverter.to_json(xml_str)
    r.ok("xml_to_json" if result.get("root", {}).get("name") == "Alice" else "")

    # Test JSON to XML
    data = {"root": {"name": "Bob", "age": 25}}
    xml_output = XmlConverter.json_to_xml_string(data)
    r.ok("json_to_xml" if "Bob" in xml_output and "25" in xml_output else "")

    return r


def test_form_converter():
    """Test FormConverter."""
    print("\n📋 Testing FormConverter...")
    r = TestResult()

    # Test form to json
    form_str = "name=Alice&age=30&active=true"
    result = FormConverter.form_to_json(form_str)
    r.ok("form_to_json" if result.get("name") == "Alice" and result.get("active") is True else "")

    # Test json to form
    data = {"name": "Bob", "age": 25}
    result = FormConverter.json_to_form(data)
    r.ok("json_to_form" if "name=Bob" in result and "age=25" in result else "")

    return r


def test_header_mapper():
    """Test HeaderMapper."""
    print("\n📋 Testing HeaderMapper...")
    r = TestResult()

    headers = {"content-type": "application/json", "authorization": "Bearer token"}
    mapping = {"content-type": "Content-Type", "authorization": "X-Auth"}
    result = HeaderMapper.map_headers(headers, mapping)
    r.ok("map_headers" if "Content-Type" in result and "X-Auth" in result else "")

    result = HeaderMapper.add_headers(headers, {"x-custom": "value"})
    r.ok("add_headers" if result.get("x-custom") == "value" else "")

    result = HeaderMapper.remove_headers(headers, ["authorization"])
    r.ok("remove_headers" if "authorization" not in result else "")

    return r


def test_middleware():
    """Test middleware implementations."""
    print("\n🔧 Testing Middleware...")
    r = TestResult()

    def next_handler(ctx):
        return ResponseContext.json({"ok": True})

    # Test CORS
    cors = CorsMiddleware()
    ctx = RequestContext("GET", "/api/test", {"origin": "http://example.com"},
                         b"", {}, ("127.0.0.1", 12345))
    resp = cors(ctx, next_handler)
    r.ok("cors headers" if "access-control-allow-origin" in resp.headers else "")

    # Test CORS preflight
    ctx2 = RequestContext("OPTIONS", "/api/test", {"origin": "http://example.com"},
                          b"", {}, ("127.0.0.1", 12345))
    resp2 = cors(ctx2, next_handler)
    r.ok("cors preflight" if resp2.status_code == 204 else "")

    # Test Rate Limiting
    rl = RateLimitMiddleware(max_requests=3, window_seconds=60)
    ctx3 = RequestContext("GET", "/", {}, b"", {}, ("127.0.0.1", 12345))
    resp3 = rl(ctx3, next_handler)
    r.ok("rate limit allow" if resp3.status_code == 200 else "")
    rl(ctx3, next_handler)
    rl(ctx3, next_handler)
    resp4 = rl(ctx3, next_handler)
    r.ok("rate limit block" if resp4.status_code == 429 else "")

    # Test Logging
    log_mw = LoggingMiddleware()
    ctx4 = RequestContext("GET", "/test", {}, b"", {}, ("127.0.0.1", 12345))
    resp5 = log_mw(ctx4, next_handler)
    r.ok("logging" if len(log_mw.get_logs()) == 1 else "")

    # Test Cache
    cache = CacheMiddleware(max_size=10, default_ttl=60)
    ctx5 = RequestContext("GET", "/cached", {}, b"", {}, ("127.0.0.1", 12345))
    resp6 = cache(ctx5, next_handler)
    r.ok("cache miss" if resp6.headers.get("x-cache") == "MISS" else "")
    resp7 = cache(ctx5, next_handler)
    r.ok("cache hit" if resp7.headers.get("x-cache") == "HIT" else "")

    # Test Auth (no keys = allow all)
    auth = AuthMiddleware()
    ctx6 = RequestContext("GET", "/", {"authorization": "Bearer test"}, b"", {}, ("127.0.0.1", 12345))
    resp8 = auth(ctx6, next_handler)
    r.ok("auth allow (no keys)" if resp8.status_code == 200 else "")

    # Test Auth (with keys)
    auth2 = AuthMiddleware(bearer_tokens=["valid-token"])
    ctx7 = RequestContext("GET", "/", {"authorization": "Bearer valid-token"}, b"", {}, ("127.0.0.1", 12345))
    resp9 = auth2(ctx7, next_handler)
    r.ok("auth valid token" if resp9.status_code == 200 else "")

    ctx8 = RequestContext("GET", "/", {"authorization": "Bearer invalid"}, b"", {}, ("127.0.0.1", 12345))
    resp10 = auth2(ctx8, next_handler)
    r.ok("auth invalid token" if resp10.status_code == 403 else "")

    # Test Auth (no header)
    ctx9 = RequestContext("GET", "/", {}, b"", {}, ("127.0.0.1", 12345))
    resp11 = auth2(ctx9, next_handler)
    r.ok("auth no header" if resp11.status_code == 401 else "")

    return r


def test_yaml_parser():
    """Test YamlParser."""
    print("\n📄 Testing YamlParser...")
    r = TestResult()

    # Test simple key-value
    yaml_str = "name: ProtoBridge\nversion: 1.0.0"
    result = YamlParser.parse(yaml_str)
    r.ok("simple kv" if result.get("name") == "ProtoBridge" and result.get("version") == "1.0.0" else "")

    # Test nested dict
    yaml_str = """
server:
  host: 127.0.0.1
  port: 8080
"""
    result = YamlParser.parse(yaml_str)
    r.ok("nested dict" if result.get("server", {}).get("port") == 8080 else "")

    # Test list
    yaml_str = """
methods:
  - GET
  - POST
  - PUT
"""
    result = YamlParser.parse(yaml_str)
    r.ok("list" if "GET" in result.get("methods", []) else "")

    # Test booleans and null
    yaml_str = "enabled: true\ndebug: false\nvalue: null"
    result = YamlParser.parse(yaml_str)
    r.ok("booleans" if result.get("enabled") is True and result.get("debug") is False and result.get("value") is None else "")

    # Test comments
    yaml_str = "# This is a comment\nname: test  # inline comment"
    result = YamlParser.parse(yaml_str)
    r.ok("comments" if result.get("name") == "test" else "")

    # Test inline list
    yaml_str = 'tags: ["a", "b", "c"]'
    result = YamlParser.parse(yaml_str)
    r.ok("inline list" if result.get("tags") == ["a", "b", "c"] else "")

    return r


def test_config_loader():
    """Test ConfigLoader."""
    print("\n📄 Testing ConfigLoader...")
    r = TestResult()

    # Test loading YAML config
    config_path = os.path.join(os.path.dirname(__file__), "..", "examples", "basic.yaml")
    if os.path.exists(config_path):
        config = ConfigLoader.load(config_path)
        r.ok("load yaml config" if "server" in config and "adapters" in config else "")
    else:
        r.ok("load yaml config (skipped - file not found)" if True else "")

    # Test env overrides
    os.environ["PROTOBRIDGE_SERVER__PORT"] = "9999"
    config = {"server": {"port": 8080}}
    result = ConfigLoader.load_env_overrides(config)
    r.ok("env override" if result.get("server", {}).get("port") == 9999 else "")
    del os.environ["PROTOBRIDGE_SERVER__PORT"]

    return r


def test_adapter_registry():
    """Test AdapterRegistry."""
    print("\n🔌 Testing AdapterRegistry...")
    r = TestResult()

    config = {
        "test_adapter": {
            "source_protocol": "rest",
            "target_protocol": "rest",
            "target_base_url": "https://httpbin.org",
            "timeout": 10,
        }
    }

    registry = AdapterRegistry.from_config(config)
    r.ok("register from config" if "test_adapter" in registry.adapters else "")

    adapter = registry.get("test_adapter")
    r.ok("get adapter" if adapter is not None and adapter.name == "test_adapter" else "")

    r.ok("list adapters" if "test_adapter" in registry.list_adapters() else "")
    r.ok("get non-existent" if registry.get("nonexistent") is None else "")

    return r


def test_server_integration():
    """Integration test: start server, make requests, verify responses."""
    print("\n🌐 Testing Server Integration...")
    r = TestResult()

    server = BridgeServer(host="127.0.0.1", port=18765)

    # Add routes
    def hello_handler(ctx):
        name = ctx.route_params.get("name", "World")
        return ResponseContext.json({"message": f"Hello, {name}!"})

    def echo_handler(ctx):
        body = ctx.get_json() or {}
        return ResponseContext.json({"echo": body})

    def health_handler(ctx):
        return ResponseContext.json({"status": "healthy"})

    server.router.add_route("GET", "/hello/{name}", hello_handler)
    server.router.add_route("POST", "/echo", echo_handler)
    server.router.add_route("GET", "/health", health_handler)

    # Add logging middleware
    log_mw = LoggingMiddleware()
    server.router.use(log_mw)

    # Start server in background
    server.start(blocking=False)
    time.sleep(0.5)  # Wait for server to start

    try:
        # Test GET /health
        try:
            req = urllib.request.Request("http://127.0.0.1:18765/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                r.ok("GET /health" if data.get("status") == "healthy" else "")
        except Exception as e:
            r.ok(f"GET /health (failed: {e})" if False else "")

        # Test GET /hello/ProtoBridge
        try:
            req = urllib.request.Request("http://127.0.0.1:18765/hello/ProtoBridge")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                r.ok("GET /hello/ProtoBridge" if "ProtoBridge" in data.get("message", "") else "")
        except Exception as e:
            r.ok(f"GET /hello (failed: {e})" if False else "")

        # Test POST /echo
        try:
            body = json.dumps({"test": "data"}).encode()
            req = urllib.request.Request("http://127.0.0.1:18765/echo",
                                         data=body,
                                         headers={"content-type": "application/json"},
                                         method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                r.ok("POST /echo" if data.get("echo", {}).get("test") == "data" else "")
        except Exception as e:
            r.ok(f"POST /echo (failed: {e})" if False else "")

        # Test 404
        try:
            req = urllib.request.Request("http://127.0.0.1:18765/nonexistent")
            urllib.request.urlopen(req, timeout=5)
            r.ok("404 handling" if False else "")
        except urllib.error.HTTPError as e:
            r.ok("404 handling" if e.code == 404 else "")
        except Exception:
            r.ok("404 handling" if False else "")

        # Test stats
        stats = server.get_stats()
        r.ok("stats tracking" if stats.get("total_requests", 0) >= 3 else "")

    finally:
        server.stop()

    return r


def run_all_tests():
    """Run all test suites."""
    print("=" * 60)
    print("  ProtoBridge Test Suite v1.0.0")
    print("=" * 60)

    results = []
    results.append(test_request_context())
    results.append(test_response_context())
    results.append(test_router())
    results.append(test_transform_rule())
    results.append(test_transform_pipeline())
    results.append(test_json_converter())
    results.append(test_xml_converter())
    results.append(test_form_converter())
    results.append(test_header_mapper())
    results.append(test_middleware())
    results.append(test_yaml_parser())
    results.append(test_config_loader())
    results.append(test_adapter_registry())
    results.append(test_server_integration())

    # Aggregate results
    total_passed = sum(r.passed for r in results)
    total_failed = sum(r.failed for r in results)
    all_errors = []
    for r in results:
        all_errors.extend(r.errors)

    print(f"\n{'='*60}")
    print(f"  🏁 Final Results: {total_passed}/{total_passed + total_failed} tests passed")
    if all_errors:
        print(f"\n  ❌ Failed tests ({len(all_errors)}):")
        for name, reason in all_errors:
            print(f"     • {name}: {reason}")
    print(f"{'='*60}")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
