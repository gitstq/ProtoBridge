"""
ProtoBridge CLI - Main entry point.

Usage:
    protobridge serve [config.yaml]  Start the bridge server
    protobridge init                 Create a starter config file
    protobridge test [config.yaml]   Test configuration validity
    protobridge list                 List available adapters
    protobridge version              Show version info
"""

import json
import os
import sys
import time
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protobridge import __version__
from protobridge.core.server import BridgeServer, RequestContext, ResponseContext
from protobridge.core.adapter import AdapterRegistry, ProtocolAdapter
from protobridge.middleware import (
    CorsMiddleware, RateLimitMiddleware, LoggingMiddleware,
    CacheMiddleware, AuthMiddleware, RetryMiddleware
)
from protobridge.utils import ConfigLoader, ColorFormatter, TableFormatter


def cmd_version(args):
    """Show version information."""
    c = ColorFormatter
    print(c.format("ProtoBridge", "bold", "cyan"))
    print(f"  Version:    {c.format(__version__, 'green')}")
    print(f"  Python:     {sys.version.split()[0]}")
    print(f"  Author:     gitstq")
    print(f"  License:    MIT")
    print(f"  Description: Lightweight Universal Protocol Adaptation & API Transformation Engine")


def cmd_init(args):
    """Create a starter configuration file."""
    config_name = args.name if hasattr(args, 'name') and args.name else "protobridge"
    config_path = f"{config_name}.yaml"

    if os.path.exists(config_path):
        print(f"⚠️  Configuration file '{config_path}' already exists.")
        return

    starter_config = '''# ProtoBridge Configuration
# Lightweight Universal Protocol Adaptation & API Transformation Engine

# Server settings
server:
  host: "127.0.0.1"
  port: 8080

# Middleware configuration
middleware:
  cors:
    enabled: true
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allowed_headers: ["Content-Type", "Authorization"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  logging:
    enabled: true
    log_body: false
  cache:
    enabled: false
    max_size: 1000
    ttl: 300
  auth:
    enabled: false
    api_keys: []
    bearer_tokens: []

# Protocol adapters
adapters:
  # Example: REST API protocol adapter
  example_adapter:
    source_protocol: "rest"
    target_protocol: "rest"
    target_base_url: "https://jsonplaceholder.typicode.com"
    strip_prefix: "/api"
    add_prefix: ""
    timeout: 30
    forward_headers:
      - "authorization"
      - "content-type"
    default_headers:
      x-custom-header: "ProtoBridge/1.0"
    request_transforms:
      - type: "rename"
        source: "user_name"
        target: "name"
      - type: "copy"
        source: "email_address"
        target: "email"
    response_transforms:
      - type: "move"
        source: "data.items"
        target: "results"
      - type: "remove"
        source: "metadata.internal"

# Routes configuration
routes:
  - method: "GET"
    path: "/api/posts"
    adapter: "example_adapter"
    description: "List all posts (proxied)"

  - method: "GET"
    path: "/api/posts/{id}"
    adapter: "example_adapter"
    description: "Get a single post by ID"

  - method: "POST"
    path: "/api/posts"
    adapter: "example_adapter"
    description: "Create a new post"

  - method: "GET"
    path: "/health"
    description: "Health check endpoint (built-in)"

  - method: "GET"
    path: "/stats"
    description: "Server statistics (built-in)"

  - method: "GET"
    path: "/adapters"
    description: "List registered adapters (built-in)"
'''

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(starter_config)

    print(f"✅ Starter configuration created: {config_path}")
    print(f"   Edit the file and run: protobridge serve {config_path}")


def cmd_test(args):
    """Test configuration file validity."""
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        return

    try:
        config = ConfigLoader.load(config_path)
        print(f"✅ Configuration loaded successfully: {config_path}")

        # Validate structure
        errors = []
        warnings = []

        if "server" not in config:
            errors.append("Missing 'server' section")
        else:
            server = config["server"]
            if "port" not in server:
                errors.append("Missing 'server.port'")
            if "host" not in server:
                warnings.append("Missing 'server.host', using default: 127.0.0.1")

        if "adapters" not in config:
            warnings.append("No adapters defined")
        else:
            for name, adapter_cfg in config["adapters"].items():
                if "target_base_url" not in adapter_cfg:
                    errors.append(f"Adapter '{name}': missing 'target_base_url'")

        if "routes" not in config:
            warnings.append("No routes defined")
        else:
            for i, route in enumerate(config["routes"]):
                if "method" not in route:
                    errors.append(f"Route #{i+1}: missing 'method'")
                if "path" not in route:
                    errors.append(f"Route #{i+1}: missing 'path'")

        if errors:
            print(f"\n❌ Validation errors ({len(errors)}):")
            for err in errors:
                print(f"   • {err}")

        if warnings:
            print(f"\n⚠️  Warnings ({len(warnings)}):")
            for warn in warnings:
                print(f"   • {warn}")

        if not errors:
            print(f"\n✅ All validation checks passed!")
            adapters = config.get("adapters", {})
            routes = config.get("routes", [])
            print(f"   Adapters: {len(adapters)}")
            print(f"   Routes:   {len(routes)}")
            print(f"   Server:   {config.get('server', {}).get('host', '127.0.0.1')}:{config.get('server', {}).get('port', 8080)}")

    except Exception as e:
        print(f"❌ Failed to parse configuration: {e}")


def cmd_list(args):
    """List available adapters from config."""
    config_path = args.config if hasattr(args, 'config') and args.config else "protobridge.yaml"
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print(f"   Run 'protobridge init' to create one.")
        return

    try:
        config = ConfigLoader.load(config_path)
        adapters = config.get("adapters", {})
        routes = config.get("routes", [])

        if not adapters:
            print("📋 No adapters configured.")
            return

        print(f"📋 Registered Adapters ({len(adapters)}):")
        print()
        headers = ["Name", "Source", "Target", "Base URL"]
        rows = []
        for name, cfg in adapters.items():
            rows.append([
                name,
                cfg.get("source_protocol", "-"),
                cfg.get("target_protocol", "-"),
                cfg.get("target_base_url", "-"),
            ])
        print(TableFormatter.format(headers, rows))

        print(f"\n🛣️  Configured Routes ({len(routes)}):")
        print()
        headers = ["Method", "Path", "Adapter", "Description"]
        rows = []
        for route in routes:
            rows.append([
                route.get("method", "-"),
                route.get("path", "-"),
                route.get("adapter", "-"),
                route.get("description", "-"),
            ])
        print(TableFormatter.format(headers, rows))

    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")


def cmd_serve(args):
    """Start the ProtoBridge server."""
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"❌ Configuration file not found: {config_path}")
        print(f"   Run 'protobridge init' to create one.")
        return

    c = ColorFormatter

    # Load configuration
    try:
        config = ConfigLoader.load(config_path)
        config = ConfigLoader.load_env_overrides(config)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return

    # Create server
    server_cfg = config.get("server", {})
    host = server_cfg.get("host", "127.0.0.1")
    port = int(server_cfg.get("port", 8080))

    server = BridgeServer(host=host, port=port)

    # Setup middleware
    middleware_cfg = config.get("middleware", {})

    if middleware_cfg.get("cors", {}).get("enabled", False):
        cors_cfg = middleware_cfg["cors"]
        server.router.use(CorsMiddleware(
            allowed_origins=cors_cfg.get("allowed_origins", ["*"]),
            allowed_methods=cors_cfg.get("allowed_methods"),
            allowed_headers=cors_cfg.get("allowed_headers"),
        ))
        print(f"  ✅ CORS middleware enabled")

    logging_mw = None
    if middleware_cfg.get("logging", {}).get("enabled", True):
        log_cfg = middleware_cfg["logging"]
        logging_mw = LoggingMiddleware(
            log_body=log_cfg.get("log_body", False),
        )
        server.router.use(logging_mw)
        print(f"  ✅ Logging middleware enabled")

    if middleware_cfg.get("rate_limit", {}).get("enabled", False):
        rl_cfg = middleware_cfg["rate_limit"]
        server.router.use(RateLimitMiddleware(
            max_requests=rl_cfg.get("max_requests", 100),
            window_seconds=rl_cfg.get("window_seconds", 60),
        ))
        print(f"  ✅ Rate limiting enabled ({rl_cfg.get('max_requests', 100)} req/{rl_cfg.get('window_seconds', 60)}s)")

    if middleware_cfg.get("cache", {}).get("enabled", False):
        cache_cfg = middleware_cfg["cache"]
        server.router.use(CacheMiddleware(
            max_size=cache_cfg.get("max_size", 1000),
            default_ttl=cache_cfg.get("ttl", 300),
        ))
        print(f"  ✅ Cache middleware enabled")

    if middleware_cfg.get("auth", {}).get("enabled", False):
        auth_cfg = middleware_cfg["auth"]
        server.router.use(AuthMiddleware(
            api_keys=auth_cfg.get("api_keys"),
            bearer_tokens=auth_cfg.get("bearer_tokens"),
        ))
        print(f"  ✅ Authentication middleware enabled")

    # Setup adapters
    adapters_cfg = config.get("adapters", {})
    registry = AdapterRegistry.from_config(adapters_cfg)

    print(f"\n  📋 Registered {len(registry.adapters)} adapter(s):")
    for name, adapter in registry.adapters.items():
        print(f"     • {c.format(name, 'green')}: {adapter.source_protocol} → {adapter.target_protocol}")
        print(f"       Target: {adapter.target_base_url}")

    # Setup routes
    routes_cfg = config.get("routes", [])
    route_count = 0

    for route_cfg in routes_cfg:
        method = route_cfg.get("method", "GET").upper()
        path = route_cfg.get("path", "/")
        adapter_name = route_cfg.get("adapter", "")

        if adapter_name and adapter_name in registry.adapters:
            adapter = registry.get(adapter_name)
            server.router.add_route(method, path, adapter.proxy_request)
            route_count += 1
        elif not adapter_name:
            # Built-in routes
            if path == "/health":
                def health_handler(ctx):
                    return ResponseContext.json({
                        "status": "healthy",
                        "version": __version__,
                        "uptime": time.time(),
                    })
                server.router.add_route(method, path, health_handler)
                route_count += 1
            elif path == "/stats":
                def stats_handler(ctx):
                    return ResponseContext.json(server.get_stats())
                server.router.add_route(method, path, stats_handler)
                route_count += 1
            elif path == "/adapters":
                def adapters_handler(ctx):
                    return ResponseContext.json({
                        "adapters": registry.list_adapters(),
                        "count": len(registry.adapters),
                    })
                server.router.add_route(method, path, adapters_handler)
                route_count += 1

    print(f"\n  🛣️  Registered {route_count} route(s)")

    # Print startup banner
    print(f"\n{'='*60}")
    print(f"  {c.format('🚀 ProtoBridge', 'bold', 'cyan')} v{__version__}")
    print(f"  Server:  {c.format(f'http://{host}:{port}', 'green')}")
    print(f"  Config:  {config_path}")
    print(f"  Routes:  {route_count}")
    print(f"{'='*60}\n")

    # Start server
    try:
        server.start(blocking=True)
    except KeyboardInterrupt:
        print(f"\n\n🛑 {c.format('Server shutting down...', 'yellow')}")
        stats = server.get_stats()
        print(f"   Total requests: {stats.get('total_requests', 0)}")
        print(f"   Avg latency:    {stats.get('avg_latency_ms', 0)}ms")
        server.stop()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="protobridge",
        description="ProtoBridge - Lightweight Universal Protocol Adaptation & API Transformation Engine",
    )
    parser.add_argument("--version", "-v", action="store_true",
                        help="Show version information")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the bridge server")
    serve_parser.add_argument("config", nargs="?", default="protobridge.yaml",
                              help="Path to configuration file")

    # init command
    init_parser = subparsers.add_parser("init", help="Create a starter configuration file")
    init_parser.add_argument("name", nargs="?", default="protobridge",
                             help="Configuration file name (without extension)")

    # test command
    test_parser = subparsers.add_parser("test", help="Test configuration validity")
    test_parser.add_argument("config", nargs="?", default="protobridge.yaml",
                             help="Path to configuration file")

    # list command
    list_parser = subparsers.add_parser("list", help="List configured adapters and routes")
    list_parser.add_argument("config", nargs="?", default="protobridge.yaml",
                             help="Path to configuration file")

    # version command
    subparsers.add_parser("version", help="Show version information")

    args = parser.parse_args()

    if args.version or args.command == "version":
        cmd_version(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "test":
        cmd_test(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()
        print(f"\n💡 Quick start: protobridge init && protobridge serve protobridge.yaml")


if __name__ == "__main__":
    main()
