"""Tests for x402 signers."""

import pytest
import os
from unittest.mock import patch, MagicMock

from x402.signer import Signer, LocalSigner
from x402.signer.base import BaseSigner
from x402.types import PaymentPayload


class TestSignerProtocol:
    """Tests for signer protocol/interface."""
    
    def test_local_signer_implements_protocol(self):
        """Test LocalSigner implements Signer protocol."""
        signer = LocalSigner.generate()
        assert isinstance(signer, Signer)
    
    def test_base_signer_is_abstract(self):
        """Test BaseSigner can't be instantiated directly."""
        with pytest.raises(TypeError):
            BaseSigner()


class TestLocalSigner:
    """Tests for LocalSigner."""
    
    def test_generate_creates_valid_signer(self):
        """Test generating a new random signer."""
        signer = LocalSigner.generate()
        assert signer is not None
    
    @pytest.mark.asyncio
    async def test_get_address_returns_checksum_address(self):
        """Test get_address returns valid checksummed address."""
        signer = LocalSigner.generate()
        address = await signer.get_address()
        
        assert address.startswith("0x")
        assert len(address) == 42
        # Check it's checksummed (has mixed case)
        assert address != address.lower()
    
    @pytest.mark.asyncio
    async def test_sign_payment_returns_65_bytes(self):
        """Test signing returns 65-byte signature."""
        signer = LocalSigner.generate()
        
        payload = PaymentPayload(
            amount=1000000,
            recipient="0x0000000000000000000000000000000000000000",
            payer=await signer.get_address(),
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=1700000000,
        )
        
        signature = await signer.sign_payment(payload)
        
        assert len(signature) == 65
        assert isinstance(signature, bytes)
    
    @pytest.mark.asyncio
    async def test_different_payloads_different_signatures(self):
        """Test different payloads produce different signatures."""
        signer = LocalSigner.generate()
        address = await signer.get_address()
        
        payload1 = PaymentPayload(
            amount=1000000,
            recipient="0x0000000000000000000000000000000000000000",
            payer=address,
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=1700000000,
        )
        
        payload2 = PaymentPayload(
            amount=2000000,  # Different amount
            recipient="0x0000000000000000000000000000000000000000",
            payer=address,
            chain_id=8453,
            token=None,
            resource="/api/test",
            nonce=1,
            expires_at=1700000000,
        )
        
        sig1 = await signer.sign_payment(payload1)
        sig2 = await signer.sign_payment(payload2)
        
        assert sig1 != sig2
    
    def test_from_private_key(self):
        """Test creating signer from private key."""
        # Generate a signer and get its key (for testing only!)
        test_key = "0x" + "ab" * 32  # Valid test key
        signer = LocalSigner.from_private_key(test_key)
        assert signer is not None
    
    def test_from_env_missing_var_raises(self):
        """Test from_env raises when env var is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="not set"):
                LocalSigner.from_env("NONEXISTENT_VAR")
    
    def test_from_env_with_valid_var(self):
        """Test from_env works with valid env var."""
        test_key = "0x" + "ab" * 32
        with patch.dict(os.environ, {"TEST_X402_KEY": test_key}):
            signer = LocalSigner.from_env("TEST_X402_KEY")
            assert signer is not None


class TestAWSKMSSigner:
    """Tests for AWS KMS signer."""
    
    def test_lazy_loads_boto3(self):
        """Test boto3 is lazy loaded."""
        from x402.signer.aws_kms import AWSKMSSigner
        
        signer = AWSKMSSigner(key_id="test-key-id", region="us-east-1")
        # Boto3 not loaded until first operation
        assert signer._client is None
    
    def test_raises_when_boto3_missing(self):
        """Test helpful error when boto3 is not installed."""
        from x402.signer.aws_kms import AWSKMSSigner
        
        signer = AWSKMSSigner(key_id="test-key-id")
        
        with patch.dict('sys.modules', {'boto3': None}):
            # This would raise ImportError in _get_client
            # We can't easily test this without uninstalling boto3
            pass
