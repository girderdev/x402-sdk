# x402 Python SDK

Pay for APIs with crypto using the x402 Payment Protocol.

## Installation

```bash
pip install x402
```

For AWS KMS signer support:
```bash
pip install x402[aws]
```

## Quick Start

### As a Client (Paying for APIs)

```python
from x402 import X402Client
from x402.signer import LocalSigner

# Create a signer (use KMS/Vault in production!)
signer = LocalSigner.from_env("X402_PRIVATE_KEY")

# Create client
client = X402Client(signer=signer)

# Make requests - SDK handles 402 responses automatically
response = await client.get("https://api.example.com/premium-data")
print(response.json())
```

### Using AWS KMS (Production)

```python
from x402 import X402Client
from x402.signer.aws_kms import AWSKMSSigner

signer = AWSKMSSigner(
    key_id="arn:aws:kms:us-east-1:123456789:key/abc-123",
    region="us-east-1"
)

client = X402Client(signer=signer)
```

### Server-Side Verification

```python
from x402 import verify_payment, PaymentRequirements

requirements = PaymentRequirements(
    amount=1000000,  # in wei
    recipient="0x...",
    network="base",
    resource="/api/data"
)

# Verify incoming payment header
payer_address = verify_payment(
    payment_header=request.headers["X-Payment"],
    requirements=requirements
)
```

## Signer Interface

The SDK uses a signer interface - your private key never touches the SDK:

```python
from x402.signer import Signer

class MySigner(Signer):
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        # Call your KMS/HSM/Vault
        return signature
    
    async def get_address(self) -> str:
        return "0x..."
```

## License

MIT
