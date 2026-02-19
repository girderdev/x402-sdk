"""Tests for x402 types."""

import pytest
from x402.types import Network, PaymentRequirements, PaymentPayload


def test_network_chain_id():
    """Test network chain ID mapping."""
    assert Network.BASE.chain_id == 8453
    assert Network.ETHEREUM.chain_id == 1
    assert Network.BASE_SEPOLIA.chain_id == 84532


def test_network_from_chain_id():
    """Test network lookup by chain ID."""
    assert Network.from_chain_id(8453) == Network.BASE
    assert Network.from_chain_id(1) == Network.ETHEREUM
    assert Network.from_chain_id(999999) is None


def test_payment_requirements():
    """Test payment requirements serialization."""
    requirements = PaymentRequirements(
        amount=1000000,
        recipient="0x0000000000000000000000000000000000000000",
        network=Network.BASE,
        resource="/api/test",
        description="Test payment",
    )
    
    assert requirements.amount == 1000000
    assert requirements.network == Network.BASE
    
    # Test JSON serialization
    json_str = requirements.model_dump_json()
    assert "1000000" in json_str
    assert "base" in json_str


def test_payment_payload_message_hash():
    """Test payment payload message hashing."""
    payload = PaymentPayload(
        amount=1000000,
        recipient="0x0000000000000000000000000000000000000000",
        payer="0x0000000000000000000000000000000000000001",
        chain_id=8453,
        token=None,
        resource="/api/test",
        nonce=1,
        expires_at=1700000000,
    )
    
    hash1 = payload.message_hash()
    assert len(hash1) == 32
    
    # Same payload should produce same hash
    hash2 = payload.message_hash()
    assert hash1 == hash2
    
    # Different payload should produce different hash
    payload2 = PaymentPayload(
        amount=2000000,  # Different amount
        recipient="0x0000000000000000000000000000000000000000",
        payer="0x0000000000000000000000000000000000000001",
        chain_id=8453,
        token=None,
        resource="/api/test",
        nonce=1,
        expires_at=1700000000,
    )
    hash3 = payload2.message_hash()
    assert hash1 != hash3
