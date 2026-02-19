"""Signature verification for x402 payments.

This module uses the native Rust implementation via FFI when available,
falling back to pure Python for compatibility.
"""

import time
from typing import Optional

from eth_account.messages import encode_defunct
from eth_account import Account

from x402.types import PaymentRequirements, SignedPayment
from x402.protocol import decode_payment_header

# Try to import native Rust bindings
try:
    from x402_native import (
        verify_signed_payment as _native_verify,
        PaymentRequirements as NativePaymentRequirements,
    )
    _USE_NATIVE = True
except ImportError:
    _USE_NATIVE = False


class X402VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class PaymentExpiredError(X402VerificationError):
    """Payment has expired."""
    pass


class InsufficientAmountError(X402VerificationError):
    """Payment amount is insufficient."""
    
    def __init__(self, required: int, provided: int):
        self.required = required
        self.provided = provided
        super().__init__(f"Insufficient amount: required {required}, got {provided}")


class InvalidSignatureError(X402VerificationError):
    """Signature is invalid."""
    pass


def verify_payment(
    payment_header: str,
    requirements: PaymentRequirements,
    current_time: Optional[int] = None,
) -> str:
    """Verify a signed payment against requirements.
    
    Uses native Rust implementation when available.
    
    Args:
        payment_header: The X-Payment header value
        requirements: Payment requirements to verify against
        current_time: Current unix timestamp (defaults to now)
        
    Returns:
        The verified payer address
        
    Raises:
        PaymentExpiredError: If payment has expired
        InsufficientAmountError: If amount is insufficient
        InvalidSignatureError: If signature is invalid
    """
    if _USE_NATIVE:
        # Use Rust implementation for verification
        try:
            native_req = NativePaymentRequirements(
                amount=requirements.amount,
                recipient=requirements.recipient,
                network=requirements.network.value if hasattr(requirements.network, 'value') else str(requirements.network),
                resource=requirements.resource,
                token=requirements.token,
                description=requirements.description,
                expires_at=requirements.expires_at,
            )
            return _native_verify(payment_header, native_req)
        except ValueError as e:
            error_msg = str(e)
            if "expired" in error_msg.lower():
                raise PaymentExpiredError(error_msg)
            elif "insufficient" in error_msg.lower():
                raise InsufficientAmountError(0, 0)  # TODO: parse amounts
            else:
                raise InvalidSignatureError(error_msg)
    
    # Fallback: pure Python implementation
    # Decode the payment
    signed_payment = decode_payment_header(payment_header)
    payment = signed_payment.payment
    
    # Check expiry
    now = current_time or int(time.time())
    if payment.expires_at < now:
        raise PaymentExpiredError("Payment has expired")
    
    # Check amount
    if payment.amount < requirements.amount:
        raise InsufficientAmountError(requirements.amount, payment.amount)
    
    # Check recipient
    if payment.recipient.lower() != requirements.recipient.lower():
        raise InvalidSignatureError(
            f"Recipient mismatch: expected {requirements.recipient}, got {payment.recipient}"
        )
    
    # Check network
    expected_chain_id = requirements.network.chain_id if hasattr(requirements.network, 'chain_id') else _get_chain_id(requirements.network)
    if payment.chain_id != expected_chain_id:
        raise InvalidSignatureError(
            f"Chain ID mismatch: expected {expected_chain_id}, got {payment.chain_id}"
        )
    
    # Verify signature and recover address
    message_hash = payment.message_hash()
    
    try:
        recovered_address = Account.recover_message(
            encode_defunct(primitive=message_hash),
            signature=signed_payment.signature
        )
    except Exception as e:
        raise InvalidSignatureError(f"Failed to recover address: {e}")
    
    # Check recovered address matches payer
    if recovered_address.lower() != payment.payer.lower():
        raise InvalidSignatureError(
            f"Recovered address {recovered_address} does not match payer {payment.payer}"
        )
    
    return recovered_address


def _get_chain_id(network: str) -> int:
    """Get chain ID from network string."""
    chain_ids = {
        "ethereum": 1,
        "base": 8453,
        "base_sepolia": 84532,
        "arbitrum": 42161,
        "optimism": 10,
        "polygon": 137,
    }
    return chain_ids.get(network, 0)
