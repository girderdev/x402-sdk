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

For development (includes aiohttp for examples):
```bash
pip install x402[dev]
```

## Quick Start

### As a Client (Paying for APIs)

```python
import asyncio
from x402 import X402Client, LocalSigner

async def main():
    # Create a signer
    # Option 1: Generate new (for testing)
    signer = LocalSigner.generate()
    
    # Option 2: From environment variable (recommended)
    # signer = LocalSigner.from_env("X402_PRIVATE_KEY")
    
    # Option 3: From private key directly (NOT recommended)
    # signer = LocalSigner.from_private_key("0x...")

    async with X402Client(
        signer=signer,
        auto_pay=True,           # Automatically handle 402 responses
        max_amount=1_000_000,    # Max 1 USDC (6 decimals) per request
    ) as client:
        # Make requests - SDK handles 402 responses automatically
        response = await client.get("https://api.example.com/premium")
        print(response.json())

asyncio.run(main())
```

### Manual Payment Handling

```python
from x402 import X402Client, LocalSigner, PaymentPayload, SignedPayment
from x402.protocol import decode_requirements_header, encode_payment_header

async def manual_payment():
    signer = LocalSigner.generate()
    
    async with X402Client(
        signer=signer,
        auto_pay=False,  # Don't auto-pay
    ) as client:
        response = await client.get("https://api.example.com/premium")
        
        if response.status_code == 402:
            # Parse requirements from header
            header = response.headers.get("X-Payment-Requirements")
            requirements = decode_requirements_header(header)
            
            print(f"Payment required: {requirements.amount}")
            print(f"Recipient: {requirements.recipient}")
            
            # Decide whether to pay based on budget, approval, etc.
            if requirements.amount <= 1_000_000:  # $1 max
                # Create payment payload
                payload = PaymentPayload(
                    amount=requirements.amount,
                    recipient=requirements.recipient,
                    payer=await signer.get_address(),
                    chain_id=requirements.network.chain_id,
                    resource=requirements.resource,
                    nonce=client.get_nonce(),
                    expires_at=requirements.expires_at,
                )
                
                # Sign and retry
                signature = await signer.sign_payment(payload)
                signed = SignedPayment(payment=payload, signature=signature)
                
                response = await client.get(
                    "https://api.example.com/premium",
                    headers={"X-Payment": encode_payment_header(signed)}
                )
```

### Using AWS KMS (Production)

```python
from x402 import X402Client, AWSKMSSigner

signer = AWSKMSSigner(
    key_id="arn:aws:kms:us-east-1:123456789:key/abc-123",
    region="us-east-1"
)

async with X402Client(signer=signer) as client:
    response = await client.get("https://api.example.com/premium")
```

### Server-Side: Requiring Payment

```python
from x402 import PaymentRequirements, Network
from x402.protocol import encode_requirements_header
from x402.verify import verify_payment

# In your API endpoint
def premium_endpoint(request):
    payment_header = request.headers.get("X-Payment")
    
    if not payment_header:
        # Return 402 with requirements
        requirements = PaymentRequirements(
            amount=1000,  # $0.001 in USDC (6 decimals)
            recipient="0xYourWalletAddress",
            network=Network.BASE_SEPOLIA,
            resource=request.path,
            expires_at=int(time.time()) + 300,  # 5 minutes
        )
        return Response(
            status=402,
            headers={"X-Payment-Requirements": encode_requirements_header(requirements)}
        )
    
    # Verify the payment
    try:
        payer_address = verify_payment(payment_header, requirements)
        # Payment valid! Return the premium content
        return {"data": "premium content", "payer": payer_address}
    except Exception as e:
        return Response(status=400, body=f"Payment failed: {e}")
```

## Supported Networks

```python
from x402 import Network

Network.ETHEREUM      # Chain ID: 1
Network.BASE          # Chain ID: 8453
Network.BASE_SEPOLIA  # Chain ID: 84532 (testnet)
Network.ARBITRUM      # Chain ID: 42161
Network.OPTIMISM      # Chain ID: 10
Network.POLYGON       # Chain ID: 137
```

## Custom Signer Interface

Implement your own signer for HSMs, Vault, or other key management:

```python
from x402.signer import Signer
from x402 import PaymentPayload

class MyCustomSigner(Signer):
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        # Call your KMS/HSM/Vault to sign
        message_hash = payload.message_hash()
        signature = await my_signing_service.sign(message_hash)
        return signature  # 65 bytes: r (32) + s (32) + v (1)
    
    async def get_address(self) -> str:
        return "0x..."  # Your wallet address
```

## Examples

See [examples/](examples/) for complete working examples:

- **basic_usage.py** - Client setup, auto-pay, manual payment flow
- **e2e_example.py** - Full server + client demo with mock payments

Run the e2e example:
```bash
cd sdk/python
pip install -e ".[dev]"
python examples/e2e_example.py
```

## API Reference

### X402Client

```python
X402Client(
    signer: Signer,           # Required: signing backend
    auto_pay: bool = True,    # Auto-handle 402 responses
    max_amount: int = None,   # Max amount to auto-pay (None = unlimited)
    timeout: float = 30.0,    # Request timeout in seconds
    base_url: str = None,     # Optional base URL
)
```

### PaymentRequirements

```python
PaymentRequirements(
    amount: int,              # Amount in smallest unit (wei/USDC decimals)
    recipient: str,           # Recipient wallet address
    network: Network,         # Blockchain network
    resource: str,            # Resource being paid for
    description: str = None,  # Human-readable description
    expires_at: int = None,   # Unix timestamp expiry
    token: str = None,        # Token address (None = native)
)
```

## License

MIT
