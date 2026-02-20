"""Tests for x402 verification."""

import pytest
import time

from x402.types import Network, PaymentRequirements, PaymentPayload, SignedPayment
from x402.verify import (
    verify_payment,
    PaymentExpiredError,
    InsufficientAmountError,
    InvalidSignatureError,
)
from x402.protocol import encode_payment_header
from x402.signer import LocalSigner


class TestVerifyPayment:
    """Tests for payment verification."""
    
    @pytest.fixture
    def requirements(self):
        """Standard payment requirements."""
        return PaymentRequirements(
            amount=1000000,
            recipient="0x0000000000000000000000000000000000000000",
            network=Network.BASE,
            resource="/api/test",
        )
    
    @pytest.mark.asyncio
    async def test_expired_payment_raises(self, requirements):
        """Test expired payment raises PaymentExpiredError."""
        signer = LocalSigner.generate()
        
        payload = PaymentPayload(
            amount=1000000,
            recipient=requirements.recipient,
            payer=await signer.get_address(),
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=1000,  # Way in the past
        )
        
        signature = await signer.sign_payment(payload)
        signed = SignedPayment(payment=payload, signature=signature)
        header = encode_payment_header(signed)
        
        with pytest.raises(PaymentExpiredError):
            verify_payment(header, requirements)
    
    @pytest.mark.asyncio
    async def test_insufficient_amount_raises(self, requirements):
        """Test insufficient amount raises InsufficientAmountError."""
        signer = LocalSigner.generate()
        
        payload = PaymentPayload(
            amount=100,  # Less than required 1000000
            recipient=requirements.recipient,
            payer=await signer.get_address(),
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=int(time.time()) + 3600,
        )
        
        signature = await signer.sign_payment(payload)
        signed = SignedPayment(payment=payload, signature=signature)
        header = encode_payment_header(signed)
        
        with pytest.raises(InsufficientAmountError):
            verify_payment(header, requirements)
    
    @pytest.mark.asyncio
    async def test_wrong_recipient_raises(self, requirements):
        """Test wrong recipient raises InvalidSignatureError."""
        signer = LocalSigner.generate()
        
        payload = PaymentPayload(
            amount=1000000,
            recipient="0x1111111111111111111111111111111111111111",  # Wrong
            payer=await signer.get_address(),
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=int(time.time()) + 3600,
        )
        
        signature = await signer.sign_payment(payload)
        signed = SignedPayment(payment=payload, signature=signature)
        header = encode_payment_header(signed)
        
        with pytest.raises(InvalidSignatureError, match="[Rr]ecipient"):
            verify_payment(header, requirements)
    
    @pytest.mark.asyncio
    async def test_wrong_chain_id_raises(self, requirements):
        """Test wrong chain ID raises InvalidSignatureError."""
        signer = LocalSigner.generate()
        
        payload = PaymentPayload(
            amount=1000000,
            recipient=requirements.recipient,
            payer=await signer.get_address(),
            chain_id=1,  # Wrong - should be 8453 (Base)
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=int(time.time()) + 3600,
        )
        
        signature = await signer.sign_payment(payload)
        signed = SignedPayment(payment=payload, signature=signature)
        header = encode_payment_header(signed)
        
        with pytest.raises(InvalidSignatureError, match="[Cc]hain"):
            verify_payment(header, requirements)


class TestVerificationErrors:
    """Tests for verification error classes."""
    
    def test_payment_expired_error(self):
        """Test PaymentExpiredError."""
        error = PaymentExpiredError("Payment has expired")
        assert "expired" in str(error).lower()
    
    def test_insufficient_amount_error(self):
        """Test InsufficientAmountError."""
        error = InsufficientAmountError(required=1000, provided=100)
        assert error.required == 1000
        assert error.provided == 100
        assert "1000" in str(error)
        assert "100" in str(error)
    
    def test_invalid_signature_error(self):
        """Test InvalidSignatureError."""
        error = InvalidSignatureError("Bad signature")
        assert "Bad signature" in str(error)
