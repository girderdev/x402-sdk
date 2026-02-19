# x402-native

Native Rust bindings for the x402 Payment Protocol.

This package provides Python bindings to the Rust x402 core library using PyO3.
It's used internally by the `x402` Python SDK for high-performance protocol operations.

## Installation

```bash
pip install x402-native
```

Or build from source:

```bash
pip install maturin
maturin develop
```

## Usage

This package is typically used through the `x402` SDK, but can be used directly:

```python
from x402_native import (
    PaymentRequirements,
    PaymentPayload,
    encode_requirements,
    decode_requirements,
    verify_signed_payment,
    get_chain_id,
)

# Create payment requirements
requirements = PaymentRequirements(
    amount=1000000,
    recipient="0x...",
    network="base",
    resource="/api/data",
)

# Encode to header
header = encode_requirements(requirements)

# Get chain ID
chain_id = get_chain_id("base")  # Returns 8453
```

## Building

Requires Rust and maturin:

```bash
# Install maturin
pip install maturin

# Build and install in development mode
maturin develop

# Build wheel for distribution
maturin build --release
```

## License

MIT
