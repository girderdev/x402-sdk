"""
x402 - Pay for APIs with crypto

The x402 Python SDK provides:
- X402Client: HTTP client that handles 402 payment flows
- Signer interface: Pluggable signing backends (KMS, Vault, etc.)
- Server utilities: Payment verification for API providers
"""

from x402.types import (
    Network,
    PaymentRequirements,
    PaymentPayload,
    SignedPayment,
)
from x402.client import X402Client
from x402.verify import verify_payment
from x402.protocol import (
    encode_requirements_header,
    decode_requirements_header,
    encode_payment_header,
    decode_payment_header,
)

__version__ = "0.1.0"

__all__ = [
    # Types
    "Network",
    "PaymentRequirements",
    "PaymentPayload",
    "SignedPayment",
    # Client
    "X402Client",
    # Verification
    "verify_payment",
    # Protocol
    "encode_requirements_header",
    "decode_requirements_header",
    "encode_payment_header",
    "decode_payment_header",
]
