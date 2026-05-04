<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.8+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="License">
  <img src="https://img.shields.io/badge/dependencies-zero-red.svg" alt="Zero Dependencies">
  <img src="https://img.shields.io/badge/tests-70%20passed-brightgreen.svg" alt="Tests">
</p>

<h1 align="center">🔀 ProtoBridge</h1>

<p align="center">
  <strong>Lightweight Universal Protocol Adaptation & API Transformation Engine</strong><br>
  轻量级通用协议适配与API转换引擎
</p>

<p align="center">
  <a href="#-简体中文">简体中文</a> ·
  <a href="#-繁體中文">繁體中文</a> ·
  <a href="#-english">English</a>
</p>

---

<a id="简体中文"></a>

## 🇨🇳 简体中文

### 🎉 项目介绍

**ProtoBridge** 是一款轻量级的通用协议适配与API转换引擎，专为开发者设计，用于解决不同API服务之间的协议碎片化问题。

**解决的痛点**：
- 🔗 不同API服务提供商使用不同的请求/响应格式，集成成本高
- 🔄 需要在多个API之间做数据格式转换，代码冗余且难维护
- 🛡️ 缺乏统一的中间层来处理认证、限流、缓存等横切关注点
- 📋 API网关方案过于笨重，不适合轻量级项目

**自研差异化亮点**：
- 🚫 **零外部依赖** — 仅使用Python标准库，无需安装任何第三方包
- ⚡ **YAML驱动配置** — 通过声明式YAML文件定义协议映射，无需编写转换代码
- 🔧 **内置转换器** — JSON扁平化/嵌套化、XML↔JSON、Form↔JSON、Header映射
- 🛡️ **可插拔中间件** — CORS、限流、日志、缓存、认证、重试，按需组合
- 📊 **实时监控** — 内置健康检查、请求统计、延迟追踪
- 🧪 **开箱即用** — 5分钟完成配置，立即启动服务

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔀 **协议适配引擎** | YAML定义输入/输出协议映射，自动完成请求转换 |
| 🔄 **请求/响应管道** | 支持请求重写、头部注入、Body转换、响应格式化 |
| 📋 **内置转换器** | JSON Schema转换、XML↔JSON、Form↔JSON、Header映射 |
| 🛡️ **中间件系统** | CORS、限流、日志、缓存、认证、重试等可插拔中间件 |
| 📊 **监控仪表盘** | 实时请求统计、延迟监控、错误率追踪 |
| 🧪 **调试模式** | 请求/响应对比视图、转换规则测试 |
| 🚫 **零依赖** | 仅使用Python标准库，兼容Python 3.8+ |

### 🚀 快速开始

#### 环境要求

- Python 3.8 或更高版本
- 无需安装任何第三方依赖

#### 安装

```bash
# 克隆仓库
git clone https://github.com/gitstq/ProtoBridge.git
cd ProtoBridge

# 安装（可选，直接运行也行）
pip install -e .
```

#### 快速启动

```bash
# 1. 创建配置文件
python -m protobridge init

# 2. 启动服务
python -m protobridge serve protobridge.yaml
```

#### 使用pip安装

```bash
pip install protobridge
protobridge init
protobridge serve protobridge.yaml
```

### 📖 详细使用指南

#### 配置文件结构

```yaml
# 服务器配置
server:
  host: "127.0.0.1"
  port: 8080

# 中间件配置
middleware:
  cors:
    enabled: true
    allowed_origins: ["*"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  logging:
    enabled: true
  cache:
    enabled: false
    max_size: 1000
    ttl: 300
  auth:
    enabled: false
    api_keys: ["your-api-key"]

# 协议适配器
adapters:
  my_api:
    source_protocol: "rest"
    target_protocol: "rest"
    target_base_url: "https://api.example.com"
    strip_prefix: "/v1"
    timeout: 30
    forward_headers:
      - "authorization"
    request_transforms:
      - type: "rename"
        source: "userName"
        target: "name"
    response_transforms:
      - type: "move"
        source: "data.items"
        target: "results"

# 路由配置
routes:
  - method: "GET"
    path: "/v1/users"
    adapter: "my_api"
    description: "获取用户列表"
```

#### 请求转换规则

| 规则类型 | 说明 | 示例 |
|----------|------|------|
| `move` | 移动字段（删除原位置） | `source: "old" → target: "new"` |
| `copy` | 复制字段（保留原位置） | `source: "email" → target: "email_address"` |
| `rename` | 重命名字段 | `source: "userName" → target: "name"` |
| `remove` | 删除字段 | `source: "password"` |
| `default` | 设置默认值 | `source: "setting", default: "fallback"` |
| `template` | 模板渲染 | `source: "Hello {{name}}!" → target: "greeting"` |

#### 内置转换器使用

```python
from protobridge.converters import JsonConverter, XmlConverter, FormConverter

# JSON扁平化
flat = JsonConverter.flatten({"user": {"name": "Alice", "age": 30}})
# {"user.name": "Alice", "user.age": 30}

# JSON嵌套化
nested = JsonConverter.unflatten({"user.name": "Alice"})
# {"user": {"name": "Alice"}}

# XML转JSON
data = XmlConverter.to_json('<root><name>Alice</name></root>')

# Form转JSON
data = FormConverter.form_to_json("name=Alice&age=30")
```

#### 中间件配置

```yaml
middleware:
  cors:
    enabled: true
    allowed_origins: ["https://example.com"]
    allowed_methods: ["GET", "POST"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  cache:
    enabled: true
    max_size: 500
    ttl: 120
  auth:
    enabled: true
    api_keys: ["my-secret-key"]
    bearer_tokens: ["my-bearer-token"]
```

#### CLI命令

```bash
# 创建配置文件
protobridge init [name]

# 启动服务器
protobridge serve [config.yaml]

# 测试配置有效性
protobridge test [config.yaml]

# 列出适配器和路由
protobridge list [config.yaml]

# 查看版本信息
protobridge version
```

#### 内置端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/stats` | GET | 服务器统计信息 |
| `/adapters` | GET | 列出已注册的适配器 |

### 💡 设计思路与迭代规划

**设计理念**：
- **配置即代码** — 通过YAML声明式配置定义所有行为，降低使用门槛
- **零依赖哲学** — 仅使用标准库，确保在任何Python环境下都能运行
- **插件化架构** — 中间件和转换器均可独立插拔，按需组合
- **开发者友好** — 清晰的错误信息、详细的日志、完善的文档

**技术选型原因**：
- Python标准库 `http.server` — 零依赖HTTP服务器，适合轻量级场景
- 自研YAML解析器 — 避免引入PyYAML依赖
- 线程安全设计 — 支持并发请求处理

**后续迭代计划**：
- [ ] WebSocket协议适配支持
- [ ] gRPC协议转换
- [ ] 配置热重载
- [ ] Prometheus指标导出
- [ ] Web管理控制台
- [ ] 插件市场

### 📦 打包与部署

#### 作为库使用

```bash
pip install protobridge
```

```python
from protobridge import BridgeServer, ProtocolAdapter
from protobridge.middleware import CorsMiddleware, LoggingMiddleware

server = BridgeServer(host="0.0.0.0", port=8080)
server.router.use(CorsMiddleware())
server.router.use(LoggingMiddleware())

# 添加自定义适配器
adapter = ProtocolAdapter("my_api", {
    "target_base_url": "https://api.example.com",
    "strip_prefix": "/proxy",
})
server.router.add_route("ANY", "/proxy/{path}*", adapter.proxy_request)

server.start()
```

#### Docker部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python", "-m", "protobridge", "serve", "protobridge.yaml"]
```

#### 环境变量覆盖

```bash
# 覆盖服务器端口
export PROTOBRIDGE_SERVER__PORT=9090

# 启动服务
python -m protobridge serve protobridge.yaml
```

### 🤝 贡献指南

欢迎贡献代码！请遵循以下规范：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: 添加某个特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

**提交规范**：
- `feat:` 新增功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

<a id="繁體中文"></a>

## 🇹🇼 繁體中文

### 🎉 專案介紹

**ProtoBridge** 是一款輕量級的通用協議適配與API轉換引擎，專為開發者設計，用於解決不同API服務之間的協議碎片化問題。

**解決的痛點**：
- 🔗 不同API服務提供商使用不同的請求/回應格式，整合成本高
- 🔄 需要在多個API之間做資料格式轉換，程式碼冗餘且難維護
- 🛡️ 缺乏統一的中間層來處理認證、限流、快取等橫切關注點
- 📋 API閘道方案過於笨重，不適合輕量級專案

**自研差異化亮點**：
- 🚫 **零外部依賴** — 僅使用Python標準庫，無需安裝任何第三方套件
- ⚡ **YAML驅動配置** — 透過宣告式YAML檔案定義協議映射，無需編寫轉換程式碼
- 🔧 **內建轉換器** — JSON扁平化/巢狀化、XML↔JSON、Form↔JSON、Header映射
- 🛡️ **可插拔中介軟體** — CORS、限流、日誌、快取、認證、重試，按需組合
- 📊 **即時監控** — 內建健康檢查、請求統計、延遲追蹤
- 🧪 **開箱即用** — 5分鐘完成配置，立即啟動服務

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🔀 **協議適配引擎** | YAML定義輸入/輸出協議映射，自動完成請求轉換 |
| 🔄 **請求/回應管道** | 支援請求重寫、Header注入、Body轉換、回應格式化 |
| 📋 **內建轉換器** | JSON Schema轉換、XML↔JSON、Form↔JSON、Header映射 |
| 🛡️ **中介軟體系統** | CORS、限流、日誌、快取、認證、重試等可插拔中介軟體 |
| 📊 **監控儀表板** | 即時請求統計、延遲監控、錯誤率追蹤 |
| 🧪 **除錯模式** | 請求/回應對比檢視、轉換規則測試 |
| 🚫 **零依賴** | 僅使用Python標準庫，相容Python 3.8+ |

### 🚀 快速開始

#### 環境需求

- Python 3.8 或更高版本
- 無需安裝任何第三方依賴

#### 安裝

```bash
# 克隆倉庫
git clone https://github.com/gitstq/ProtoBridge.git
cd ProtoBridge

# 安裝（可選，直接執行也行）
pip install -e .
```

#### 快速啟動

```bash
# 1. 建立配置檔案
python -m protobridge init

# 2. 啟動服務
python -m protobridge serve protobridge.yaml
```

#### 使用pip安裝

```bash
pip install protobridge
protobridge init
protobridge serve protobridge.yaml
```

### 📖 詳細使用指南

#### 配置檔案結構

```yaml
# 伺服器配置
server:
  host: "127.0.0.1"
  port: 8080

# 中介軟體配置
middleware:
  cors:
    enabled: true
    allowed_origins: ["*"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  logging:
    enabled: true
  cache:
    enabled: false
    max_size: 1000
    ttl: 300
  auth:
    enabled: false
    api_keys: ["your-api-key"]

# 協議適配器
adapters:
  my_api:
    source_protocol: "rest"
    target_protocol: "rest"
    target_base_url: "https://api.example.com"
    strip_prefix: "/v1"
    timeout: 30
    forward_headers:
      - "authorization"
    request_transforms:
      - type: "rename"
        source: "userName"
        target: "name"
    response_transforms:
      - type: "move"
        source: "data.items"
        target: "results"

# 路由配置
routes:
  - method: "GET"
    path: "/v1/users"
    adapter: "my_api"
    description: "取得使用者列表"
```

#### 請求轉換規則

| 規則類型 | 說明 | 範例 |
|----------|------|------|
| `move` | 移動欄位（刪除原位置） | `source: "old" → target: "new"` |
| `copy` | 複製欄位（保留原位置） | `source: "email" → target: "email_address"` |
| `rename` | 重新命名欄位 | `source: "userName" → target: "name"` |
| `remove` | 刪除欄位 | `source: "password"` |
| `default` | 設定預設值 | `source: "setting", default: "fallback"` |
| `template` | 模板渲染 | `source: "Hello {{name}}!" → target: "greeting"` |

#### 內建轉換器使用

```python
from protobridge.converters import JsonConverter, XmlConverter, FormConverter

# JSON扁平化
flat = JsonConverter.flatten({"user": {"name": "Alice", "age": 30}})
# {"user.name": "Alice", "user.age": 30}

# JSON巢狀化
nested = JsonConverter.unflatten({"user.name": "Alice"})
# {"user": {"name": "Alice"}}

# XML轉JSON
data = XmlConverter.to_json('<root><name>Alice</name></root>')

# Form轉JSON
data = FormConverter.form_to_json("name=Alice&age=30")
```

#### 中介軟體配置

```yaml
middleware:
  cors:
    enabled: true
    allowed_origins: ["https://example.com"]
    allowed_methods: ["GET", "POST"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  cache:
    enabled: true
    max_size: 500
    ttl: 120
  auth:
    enabled: true
    api_keys: ["my-secret-key"]
    bearer_tokens: ["my-bearer-token"]
```

#### CLI指令

```bash
# 建立配置檔案
protobridge init [name]

# 啟動伺服器
protobridge serve [config.yaml]

# 測試配置有效性
protobridge test [config.yaml]

# 列出適配器和路由
protobridge list [config.yaml]

# 查看版本資訊
protobridge version
```

#### 內建端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康檢查 |
| `/stats` | GET | 伺服器統計資訊 |
| `/adapters` | GET | 列出已註冊的適配器 |

### 💡 設計思路與迭代規劃

**設計理念**：
- **配置即程式碼** — 透過YAML宣告式配置定義所有行為，降低使用門檻
- **零依賴哲學** — 僅使用標準庫，確保在任何Python環境下都能執行
- **外掛化架構** — 中介軟體和轉換器均可獨立插拔，按需組合
- **開發者友善** — 清晰的錯誤資訊、詳細的日誌、完善的文件

**技術選型原因**：
- Python標準庫 `http.server` — 零依賴HTTP伺服器，適合輕量級場景
- 自研YAML解析器 — 避免引入PyYAML依賴
- 執行緒安全設計 — 支援並發請求處理

**後續迭代計畫**：
- [ ] WebSocket協議適配支援
- [ ] gRPC協議轉換
- [ ] 配置熱重載
- [ ] Prometheus指標匯出
- [ ] Web管理控制台
- [ ] 外掛市場

### 📦 打包與部署

#### 作為函式庫使用

```bash
pip install protobridge
```

```python
from protobridge import BridgeServer, ProtocolAdapter
from protobridge.middleware import CorsMiddleware, LoggingMiddleware

server = BridgeServer(host="0.0.0.0", port=8080)
server.router.use(CorsMiddleware())
server.router.use(LoggingMiddleware())

# 新增自訂適配器
adapter = ProtocolAdapter("my_api", {
    "target_base_url": "https://api.example.com",
    "strip_prefix": "/proxy",
})
server.router.add_route("ANY", "/proxy/{path}*", adapter.proxy_request)

server.start()
```

#### Docker部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python", "-m", "protobridge", "serve", "protobridge.yaml"]
```

#### 環境變數覆蓋

```bash
# 覆蓋伺服器埠
export PROTOBRIDGE_SERVER__PORT=9090

# 啟動服務
python -m protobridge serve protobridge.yaml
```

### 🤝 貢獻指南

歡迎貢獻程式碼！請遵循以下規範：

1. Fork 本倉庫
2. 建立特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'feat: 新增某個特性'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 發起 Pull Request

**提交規範**：
- `feat:` 新增功能
- `fix:` 修復問題
- `docs:` 文件更新
- `refactor:` 程式碼重構
- `test:` 測試相關
- `chore:` 建構/工具相關

### 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

<a id="english"></a>

## 🇬🇧 English

### 🎉 Introduction

**ProtoBridge** is a lightweight universal protocol adaptation and API transformation engine designed for developers to solve the protocol fragmentation problem between different API services.

**Pain Points Solved**:
- 🔗 Different API providers use different request/response formats, leading to high integration costs
- 🔄 Data format conversion between multiple APIs creates redundant, hard-to-maintain code
- 🛡️ Lack of a unified middleware layer for cross-cutting concerns like auth, rate limiting, and caching
- 📋 Existing API gateway solutions are too heavyweight for lightweight projects

**Differentiation Highlights**:
- 🚫 **Zero External Dependencies** — Uses only Python standard library, no third-party packages needed
- ⚡ **YAML-Driven Configuration** — Declarative YAML files define protocol mappings, no code required
- 🔧 **Built-in Converters** — JSON flatten/nest, XML↔JSON, Form↔JSON, Header mapping
- 🛡️ **Pluggable Middleware** — CORS, rate limiting, logging, caching, auth, retry — compose as needed
- 📊 **Real-time Monitoring** — Built-in health checks, request statistics, latency tracking
- 🧪 **Ready to Use** — Configure in 5 minutes, start serving immediately

### ✨ Core Features

| Feature | Description |
|---------|-------------|
| 🔀 **Protocol Adapter Engine** | YAML-defined input/output protocol mappings with automatic request transformation |
| 🔄 **Request/Response Pipeline** | Request rewriting, header injection, body transformation, response formatting |
| 📋 **Built-in Converters** | JSON Schema transform, XML↔JSON, Form↔JSON, Header mapping |
| 🛡️ **Middleware System** | CORS, rate limiting, logging, caching, auth, retry — pluggable middleware |
| 📊 **Monitoring Dashboard** | Real-time request stats, latency monitoring, error rate tracking |
| 🧪 **Debug Mode** | Request/response diff view, transformation rule testing |
| 🚫 **Zero Dependencies** | Python standard library only, compatible with Python 3.8+ |

### 🚀 Quick Start

#### Requirements

- Python 3.8 or higher
- No third-party dependencies required

#### Installation

```bash
# Clone the repository
git clone https://github.com/gitstq/ProtoBridge.git
cd ProtoBridge

# Install (optional, works without installation too)
pip install -e .
```

#### Quick Start

```bash
# 1. Create a configuration file
python -m protobridge init

# 2. Start the server
python -m protobridge serve protobridge.yaml
```

#### Install via pip

```bash
pip install protobridge
protobridge init
protobridge serve protobridge.yaml
```

### 📖 Detailed Usage Guide

#### Configuration File Structure

```yaml
# Server settings
server:
  host: "127.0.0.1"
  port: 8080

# Middleware configuration
middleware:
  cors:
    enabled: true
    allowed_origins: ["*"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  logging:
    enabled: true
  cache:
    enabled: false
    max_size: 1000
    ttl: 300
  auth:
    enabled: false
    api_keys: ["your-api-key"]

# Protocol adapters
adapters:
  my_api:
    source_protocol: "rest"
    target_protocol: "rest"
    target_base_url: "https://api.example.com"
    strip_prefix: "/v1"
    timeout: 30
    forward_headers:
      - "authorization"
    request_transforms:
      - type: "rename"
        source: "userName"
        target: "name"
    response_transforms:
      - type: "move"
        source: "data.items"
        target: "results"

# Routes configuration
routes:
  - method: "GET"
    path: "/v1/users"
    adapter: "my_api"
    description: "List users"
```

#### Transformation Rules

| Rule Type | Description | Example |
|-----------|-------------|---------|
| `move` | Move field (remove from source) | `source: "old" → target: "new"` |
| `copy` | Copy field (keep source) | `source: "email" → target: "email_address"` |
| `rename` | Rename field | `source: "userName" → target: "name"` |
| `remove` | Remove field | `source: "password"` |
| `default` | Set default value | `source: "setting", default: "fallback"` |
| `template` | Template rendering | `source: "Hello {{name}}!" → target: "greeting"` |

#### Built-in Converters

```python
from protobridge.converters import JsonConverter, XmlConverter, FormConverter

# Flatten JSON
flat = JsonConverter.flatten({"user": {"name": "Alice", "age": 30}})
# {"user.name": "Alice", "user.age": 30}

# Unflatten JSON
nested = JsonConverter.unflatten({"user.name": "Alice"})
# {"user": {"name": "Alice"}}

# XML to JSON
data = XmlConverter.to_json('<root><name>Alice</name></root>')

# Form to JSON
data = FormConverter.form_to_json("name=Alice&age=30")
```

#### Middleware Configuration

```yaml
middleware:
  cors:
    enabled: true
    allowed_origins: ["https://example.com"]
    allowed_methods: ["GET", "POST"]
  rate_limit:
    enabled: true
    max_requests: 100
    window_seconds: 60
  cache:
    enabled: true
    max_size: 500
    ttl: 120
  auth:
    enabled: true
    api_keys: ["my-secret-key"]
    bearer_tokens: ["my-bearer-token"]
```

#### CLI Commands

```bash
# Create a configuration file
protobridge init [name]

# Start the server
protobridge serve [config.yaml]

# Test configuration validity
protobridge test [config.yaml]

# List adapters and routes
protobridge list [config.yaml]

# Show version info
protobridge version
```

#### Built-in Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Server statistics |
| `/adapters` | GET | List registered adapters |

### 💡 Design Philosophy & Roadmap

**Design Principles**:
- **Configuration as Code** — Declarative YAML defines all behavior, lowering the barrier to entry
- **Zero Dependency Philosophy** — Standard library only, runs in any Python environment
- **Plugin Architecture** — Middleware and converters are independently pluggable
- **Developer Friendly** — Clear error messages, detailed logging, comprehensive documentation

**Technology Choices**:
- Python standard library `http.server` — Zero-dependency HTTP server for lightweight use cases
- Custom YAML parser — Avoids PyYAML dependency
- Thread-safe design — Supports concurrent request handling

**Roadmap**:
- [ ] WebSocket protocol adapter support
- [ ] gRPC protocol transformation
- [ ] Hot configuration reload
- [ ] Prometheus metrics export
- [ ] Web management console
- [ ] Plugin marketplace

### 📦 Packaging & Deployment

#### Use as a Library

```bash
pip install protobridge
```

```python
from protobridge import BridgeServer, ProtocolAdapter
from protobridge.middleware import CorsMiddleware, LoggingMiddleware

server = BridgeServer(host="0.0.0.0", port=8080)
server.router.use(CorsMiddleware())
server.router.use(LoggingMiddleware())

# Add custom adapter
adapter = ProtocolAdapter("my_api", {
    "target_base_url": "https://api.example.com",
    "strip_prefix": "/proxy",
})
server.router.add_route("ANY", "/proxy/{path}*", adapter.proxy_request)

server.start()
```

#### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python", "-m", "protobridge", "serve", "protobridge.yaml"]
```

#### Environment Variable Overrides

```bash
# Override server port
export PROTOBRIDGE_SERVER__PORT=9090

# Start the server
python -m protobridge serve protobridge.yaml
```

### 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add some feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Commit Convention**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation update
- `refactor:` Code refactoring
- `test:` Test related
- `chore:` Build/tooling related

### 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/gitstq">gitstq</a>
</p>
