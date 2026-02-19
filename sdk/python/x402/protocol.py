"""x402 protocol header encoding/decoding.

This module uses the native Rust implementation via FFI when available,
falling back to pure Python for compatibility.
"""

import base64
import json
from typing import Any, Tuple

from x402.types import PaymentRequirements, SignedPayment, PaymentPayload

# Try to import native Rust bindings
try:
    from x402_native import (
        encode_requirements as _native_encode_requirements,
        decode_requirements as _native_decode_requirements,
        encode_payment as _native_encode_payment,
        decode_payment as _native_decode_payment,
        PaymentRequirements as NativePaymentRequirements,
        PaymentPayload as NativePaymentPayload,
    )
    _USE_NATIVE = True
except ImportError:
    _USE_NATIVE = False


# Header names
X402_REQUIREMENTS_HEADER = "X-Payment-Requirements"
X402_PAYMENT_HEADER = "X-Payment"


def encode_requirements_header(requirements: PaymentRequirements) -> str:
    """Encode payment requirements to header value.
    
    Uses native Rust implementation when available.
    
    Args:
        requirements: Payment requirements to encode
        
    Returns:
        Base64-encoded JSON string
    """
    if _USE_NATIVE:
        # Use Rust implementation
        native_req = NativePaymentRequirements(
            amount=requirements.amount,
            recipient=requirements.recipient,
            network=requirements.network.value if hasattr(requirements.network, 'value') else str(requirements.network),
            resource=requirements.resource,
            token=requirements.token,
            description=requirements.description,
            expires_at=requirements.expires_at,
        )
        return _native_encode_requirements(native_req)
    
    # Fallback: pure Python
    json_str = requirements.model_dump_json()
    return base64.b64encode(json_str.encode()).decode()


def decode_requirements_header(header: str) -> PaymentRequirements:
    """Decode payment requirements from header value.
    
    Uses native Rust implementation when available.
    
    Args:
        header: Base64-encoded header value
        
    Returns:
        Decoded PaymentRequirements
        
    Raises:
        ValueError: If header is invalid
    """
    if _USE_NATIVE:
        # Use Rust implementation
        native_req = _native_decode_requirements(header)
        return PaymentRequirements(
            amount=native_req.amount,
            recipient=native_req.recipient,
            network=native_req.network,
            token=None,  # TODO: handle token
            description=native_req.description,
            expires_at=native_req.expires_at,
            resource=native_req.resource,
        )
    
    # Fallback: pure Python
    try:
        json_bytes = base64.b64decode(header)
        data = json.loads(json_bytes)
        return PaymentRequirements(**data)
    except Exception as e:
        raise ValueError(f"Invalid X-Payment-Requirements header: {e}")


def encode_payment_header(payment: SignedPayment) -> str:
    """Encode signed payment to header value.
    
    Uses native Rust implementation when available.
    
    Args:
        payment: Signed payment to encode
        
    Returns:
        Base64-encoded JSON string
    """
    if _USE_NATIVE:
        # Use Rust implementation
        native_payload = NativePaymentPayload(
            amount=payment.payment.amount,
            recipient=payment.payment.recipient,
            payer=payment.payment.payer,
            chain_id=payment.payment.chain_id,
            resource=payment.payment.resource,
            nonce=payment.payment.nonce,
            expires_at=payment.payment.expires_at,
            token=payment.payment.token,
        )
        return _native_encode_payment(native_payload, payment.signature)
    
    # Fallback: pure Python
    data = {
        "payment": payment.payment.model_dump(),
        "signature": payment.signature.hex(),
    }
    json_str = json.dumps(data)
    return base64.b64encode(json_str.encode()).decode()


def decode_payment_header(header: str) -> SignedPayment:
    """Decode signed payment from header value.
    
    Uses native Rust implementation when available.
    
    Args:
        header: Base64-encoded header value
        
    Returns:
        Decoded SignedPayment
        
    Raises:
        ValueError: If header is invalid
    """
    if _USE_NATIVE:
        # Use Rust implementation
        native_payload, signature = _native_decode_payment(header)
        payload = PaymentPayload(
            amount=native_payload.amount,
            recipient=native_payload.recipient,
            payer=native_payload.payer,
            chain_id=native_payload.chain_id,
            token=None,  # TODO: handle token
            resource=native_payload.resource,
            nonce=native_payload.nonce,
            expires_at=native_payload.expires_at,
        )
        return SignedPayment(payment=payload, signature=bytes(signature))
    
    # Fallback: pure Python
    try:
        json_bytes = base64.b64decode(header)
        data = json.loads(json_bytes)
        
        payment = PaymentPayload(**data["payment"])
        signature = bytes.fromhex(data["signature"])
        
        return SignedPayment(payment=payment, signature=signature)
    except Exception as e:
        raise ValueError(f"Invalid X-Payment header: {e}")
