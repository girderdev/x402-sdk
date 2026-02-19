"""Tests for x402 protocol encoding/decoding."""

import pytest
from x402.types import Network, PaymentRequirements
from x402.protocol import (
    encode_requirements_header,
    decode_requirements_header,
)


def test_requirements_roundtrip():
    """Test encoding and decoding requirements."""
    requirements = PaymentRequirements(
        amount=1000000,
        recipient="0x0000000000000000000000000000000000000000",
        network=Network.BASE,
        resource="/api/test",
        description="Test payment",
        expires_at=1700000000,
    )
    
    # Encode
    encoded = encode_requirements_header(requirements)
    assert isinstance(encoded, str)
    
    # Decode
    decoded = decode_requirements_header(encoded)
    
    assert decoded.amount == requirements.amount
    assert decoded.recipient == requirements.recipient
    assert decoded.resource == requirements.resource
    assert decoded.description == requirements.description


def test_invalid_header():
    """Test decoding invalid header raises error."""
    with pytest.raises(ValueError):
        decode_requirements_header("not-valid-base64!!!")
    
    with pytest.raises(ValueError):
        # Valid base64 but not JSON
        import base64
        decode_requirements_header(base64.b64encode(b"not json").decode())
