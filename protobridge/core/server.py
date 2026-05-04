"""
Core HTTP server implementation for ProtoBridge.

Provides a lightweight HTTP server using only Python standard library,
capable of handling protocol adaptation, request transformation,
and response formatting.
"""

import json
import socket
import threading
import traceback
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any, Callable, Tuple


class RequestContext:
    """Represents an incoming HTTP request with parsed components."""

    def __init__(self, method: str, path: str, headers: Dict[str, str],
                 body: bytes, query_params: Dict[str, str],
                 client_address: Tuple[str, int]):
        self.method = method.upper()
        self.path = path
        self.headers = headers
        self.body = body
        self.query_params = query_params
        self.client_address = client_address
        self.attributes: Dict[str, Any] = {}
        self.start_time: float = 0.0
        self.matched_route: Optional[str] = None
        self.route_params: Dict[str, str] = {}

    def get_json(self) -> Optional[Dict[str, Any]]:
        """Parse request body as JSON."""
        try:
            return json.loads(self.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def get_form_data(self) -> Dict[str, str]:
        """Parse request body as form-urlencoded data."""
        try:
            content_type = self.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                return dict(urllib.parse.parse_qsl(self.body.decode("utf-8")))
            return {}
        except UnicodeDecodeError:
            return {}

    def get_header(self, name: str, default: str = "") -> str:
        """Get header value (case-insensitive)."""
        name_lower = name.lower()
        for key, value in self.headers.items():
            if key.lower() == name_lower:
                return value
        return default

    def __repr__(self) -> str:
        return f"RequestContext(method={self.method}, path={self.path})"


class ResponseContext:
    """Represents an HTTP response to be sent back to the client."""

    def __init__(self, status_code: int = 200, body: bytes = b"",
                 headers: Optional[Dict[str, str]] = None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}
        self.headers.setdefault("content-type", "application/json; charset=utf-8")

    @classmethod
    def json(cls, data: Any, status_code: int = 200) -> "ResponseContext":
        """Create a JSON response."""
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        return cls(status_code=status_code, body=body,
                   headers={"content-type": "application/json; charset=utf-8"})

    @classmethod
    def text(cls, text: str, status_code: int = 200) -> "ResponseContext":
        """Create a plain text response."""
        return cls(status_code=status_code, body=text.encode("utf-8"),
                   headers={"content-type": "text/plain; charset=utf-8"})

    @classmethod
    def html(cls, html: str, status_code: int = 200) -> "ResponseContext":
        """Create an HTML response."""
        return cls(status_code=status_code, body=html.encode("utf-8"),
                   headers={"content-type": "text/html; charset=utf-8"})

    @classmethod
    def error(cls, message: str, status_code: int = 500) -> "ResponseContext":
        """Create an error response."""
        return cls.json({"error": message, "status": status_code},
                        status_code=status_code)

    def __repr__(self) -> str:
        return f"ResponseContext(status={self.status_code}, body_len={len(self.body)})"


class Route:
    """Represents a single route definition with pattern matching."""

    def __init__(self, method: str, pattern: str, handler: Callable,
                 name: str = "", middleware: Optional[List[Callable]] = None):
        self.method = method.upper()
        self.pattern = pattern
        self.handler = handler
        self.name = name
        self.middleware = middleware or []
        self._pattern_parts = self._compile_pattern(pattern)

    def _compile_pattern(self, pattern: str) -> List[Tuple[str, str]]:
        """Compile route pattern into parts for matching."""
        parts = []
        for segment in pattern.strip("/").split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                param_name = segment[1:-1]
                parts.append(("param", param_name))
            elif segment.startswith("*"):
                parts.append(("wildcard", segment[1:]))
            else:
                parts.append(("literal", segment))
        return parts

    def match(self, method: str, path: str) -> Optional[Dict[str, str]]:
        """Check if this route matches the given method and path."""
        if self.method != method.upper():
            return None

        path_parts = path.strip("/").split("/")
        pattern_parts = self._pattern_parts

        # Check for wildcard match
        if pattern_parts and pattern_parts[-1][0] == "wildcard":
            if len(path_parts) < len(pattern_parts) - 1:
                return None
            params = {}
            for i, (ptype, pname) in enumerate(pattern_parts[:-1]):
                if ptype == "literal" and i < len(path_parts):
                    if path_parts[i] != pname:
                        return None
                elif ptype == "param" and i < len(path_parts):
                    params[pname] = path_parts[i]
            params[pattern_parts[-1][1]] = "/".join(path_parts[len(pattern_parts) - 1:])
            return params

        if len(path_parts) != len(pattern_parts):
            return None

        params = {}
        for (ptype, pname), path_part in zip(pattern_parts, path_parts):
            if ptype == "literal" and path_part != pname:
                return None
            elif ptype == "param":
                params[pname] = path_part

        return params

    def __repr__(self) -> str:
        return f"Route(method={self.method}, pattern={self.pattern})"


class Router:
    """HTTP request router with pattern matching and middleware support."""

    def __init__(self):
        self.routes: List[Route] = []
        self.global_middleware: List[Callable] = []

    def add_route(self, method: str, pattern: str, handler: Callable,
                  name: str = "", middleware: Optional[List[Callable]] = None):
        """Add a new route to the router."""
        route = Route(method, pattern, handler, name, middleware)
        self.routes.append(route)

    def get(self, pattern: str, name: str = "", middleware: Optional[List[Callable]] = None):
        """Decorator for GET routes."""
        def decorator(func):
            self.add_route("GET", pattern, func, name, middleware)
            return func
        return decorator

    def post(self, pattern: str, name: str = "", middleware: Optional[List[Callable]] = None):
        """Decorator for POST routes."""
        def decorator(func):
            self.add_route("POST", pattern, func, name, middleware)
            return func
        return decorator

    def put(self, pattern: str, name: str = "", middleware: Optional[List[Callable]] = None):
        """Decorator for PUT routes."""
        def decorator(func):
            self.add_route("PUT", pattern, func, name, middleware)
            return func
        return decorator

    def delete(self, pattern: str, name: str = "", middleware: Optional[List[Callable]] = None):
        """Decorator for DELETE routes."""
        def decorator(func):
            self.add_route("DELETE", pattern, func, name, middleware)
            return func
        return decorator

    def any(self, pattern: str, name: str = "", middleware: Optional[List[Callable]] = None):
        """Decorator for routes matching any method."""
        def decorator(func):
            for method in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                self.add_route(method, pattern, func, name, middleware)
            return func
        return decorator

    def use(self, middleware: Callable):
        """Add global middleware."""
        self.global_middleware.append(middleware)

    def resolve(self, method: str, path: str) -> Optional[Tuple[Route, Dict[str, str]]]:
        """Resolve a route for the given method and path."""
        for route in self.routes:
            params = route.match(method, path)
            if params is not None:
                return route, params
        return None


class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler that integrates with the ProtoBridge router."""

    router: Router = None  # Set by the server
    stats: Dict[str, Any] = None  # Shared stats dict

    def log_message(self, format, *args):
        """Override to use custom logging."""
        pass

    def _parse_request(self) -> RequestContext:
        """Parse incoming request into RequestContext."""
        content_length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        parsed = urllib.parse.urlparse(self.path)
        query_params = dict(urllib.parse.parse_qsl(parsed.query))

        headers = {}
        for key, value in self.headers.items():
            headers[key] = value

        return RequestContext(
            method=self.command,
            path=parsed.path,
            headers=headers,
            body=body,
            query_params=query_params,
            client_address=self.client_address
        )

    def _send_response(self, response: ResponseContext):
        """Send response back to client."""
        self.send_response(response.status_code)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.body)

    def _handle_request(self):
        """Core request handling logic."""
        import time
        ctx = self._parse_request()
        ctx.start_time = time.time()

        # Update stats
        if BridgeHandler.stats is not None:
            BridgeHandler.stats["total_requests"] = BridgeHandler.stats.get("total_requests", 0) + 1

        # Resolve route
        result = BridgeHandler.router.resolve(ctx.method, ctx.path)
        if result is None:
            response = ResponseContext.error("Not Found", 404)
            self._send_response(response)
            return

        route, params = result
        ctx.matched_route = route.pattern
        ctx.route_params = params

        # Execute global middleware chain
        try:
            response = self._execute_middleware(
                BridgeHandler.router.global_middleware + route.middleware,
                ctx, route.handler
            )
        except Exception as e:
            traceback.print_exc()
            response = ResponseContext.error(f"Internal Server Error: {str(e)}", 500)

        # Update stats
        if BridgeHandler.stats is not None:
            elapsed = time.time() - ctx.start_time
            BridgeHandler.stats["total_requests"] = BridgeHandler.stats.get("total_requests", 0)
            status_key = f"status_{response.status_code}"
            BridgeHandler.stats[status_key] = BridgeHandler.stats.get(status_key, 0) + 1
            route_key = f"route_{ctx.method}_{route.pattern}"
            BridgeHandler.stats[route_key] = BridgeHandler.stats.get(route_key, 0) + 1
            BridgeHandler.stats["total_latency"] = BridgeHandler.stats.get("total_latency", 0.0) + elapsed

        self._send_response(response)

    def _execute_middleware(self, middleware_chain: List[Callable],
                           ctx: RequestContext, handler: Callable) -> ResponseContext:
        """Execute middleware chain and then the handler."""
        if not middleware_chain:
            return handler(ctx)

        middleware = middleware_chain[0]
        remaining = middleware_chain[1:]

        def next_handler(request_ctx: RequestContext) -> ResponseContext:
            return self._execute_middleware(remaining, request_ctx, handler)

        return middleware(ctx, next_handler)

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

    def do_PATCH(self):
        self._handle_request()

    def do_OPTIONS(self):
        self._handle_request()

    def do_HEAD(self):
        self._handle_request()


class BridgeServer:
    """Main ProtoBridge server that manages the HTTP server lifecycle."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.router = Router()
        self.stats: Dict[str, Any] = {
            "total_requests": 0,
            "total_latency": 0.0,
        }
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def setup(self):
        """Configure the handler with router and stats."""
        BridgeHandler.router = self.router
        BridgeHandler.stats = self.stats

    def start(self, blocking: bool = True):
        """Start the ProtoBridge server."""
        self.setup()
        self._server = HTTPServer((self.host, self.port), BridgeHandler)

        if blocking:
            print(f"🚀 ProtoBridge server running at http://{self.host}:{self.port}")
            print(f"   Press Ctrl+C to stop")
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 Server shutting down...")
                self._server.shutdown()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            print(f"🚀 ProtoBridge server running at http://{self.host}:{self.port}")

    def stop(self):
        """Stop the ProtoBridge server."""
        if self._server:
            self._server.shutdown()
            print("🛑 Server stopped.")

    def get_stats(self) -> Dict[str, Any]:
        """Get current server statistics."""
        stats = dict(self.stats)
        if stats.get("total_requests", 0) > 0:
            stats["avg_latency_ms"] = round(
                stats.get("total_latency", 0) / stats["total_requests"] * 1000, 2
            )
        else:
            stats["avg_latency_ms"] = 0.0
        return stats

    def reset_stats(self):
        """Reset server statistics."""
        self.stats.clear()
        self.stats.update({"total_requests": 0, "total_latency": 0.0})
