# x402-sdk

x402 Payment Protocol SDK - Rust core with TypeScript & Python bindings.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Rust Core                               │
│  (signing, payment logic, protocol parsing)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │  PyO3   │  │ napi-rs │  │  WASM   │
    │ binding │  │ binding │  │ binding │
    └────┬────┘  └────┬────┘  └────┬────┘
         │            │            │
         ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐
    │ Python  │  │ Node.js │  │ Browser │
    │   SDK   │  │   SDK   │  │   SDK   │
    └─────────┘  └─────────┘  └─────────┘
```

## Repository Structure

```
x402-sdk/
├── spec/                  # OpenAPI spec & protocol docs
├── core/                  # Rust core implementation
├── bindings/              # FFI bindings (PyO3, napi-rs, WASM)
├── sdk/
│   ├── typescript/        # @x402/client, @x402/server, @x402/mcp
│   └── python/            # x402-client, x402-server, x402-mcp
└── docs/                  # Documentation
```

## Packages

### TypeScript/JavaScript
- `@x402/client` - Pay for x402-enabled APIs
- `@x402/server` - Monetize your APIs with x402
- `@x402/mcp` - MCP tool integration for AI agents

### Python
- `x402-client` - Pay for x402-enabled APIs
- `x402-server` - Monetize your APIs with x402
- `x402-mcp` - MCP tool integration for AI agents

## License

MIT
