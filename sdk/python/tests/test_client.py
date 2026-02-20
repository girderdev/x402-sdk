"""Tests for x402 client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from x402.client import X402Client
from x402.types import Network, PaymentRequirements
from x402.protocol import encode_requirements_header, X402_REQUIREMENTS_HEADER


@pytest.fixture
def mock_signer():
    """Create a mock signer."""
    signer = AsyncMock()
    signer.get_address.return_value = "0x1234567890123456789012345678901234567890"
    signer.sign_payment.return_value = b"\x00" * 65
    return signer


@pytest.mark.asyncio
async def test_client_init(mock_signer):
    """Test client initialization."""
    client = X402Client(signer=mock_signer)
    assert client._signer == mock_signer
    assert client._auto_pay is True
    assert client._max_amount is None
    await client.close()


@pytest.mark.asyncio
async def test_client_context_manager(mock_signer):
    """Test client as context manager."""
    async with X402Client(signer=mock_signer) as client:
        assert client is not None


@pytest.mark.asyncio
async def test_client_max_amount(mock_signer):
    """Test max_amount is respected."""
    client = X402Client(signer=mock_signer, max_amount=1000)
    assert client._max_amount == 1000
    await client.close()


@pytest.mark.asyncio
async def test_client_auto_pay_disabled(mock_signer):
    """Test auto_pay can be disabled."""
    client = X402Client(signer=mock_signer, auto_pay=False)
    assert client._auto_pay is False
    await client.close()


@pytest.mark.asyncio
async def test_client_get_nonce(mock_signer):
    """Test nonce increments."""
    client = X402Client(signer=mock_signer)
    nonce1 = client._get_nonce()
    nonce2 = client._get_nonce()
    assert nonce2 > nonce1
    await client.close()


class TestClientPaymentFlow:
    """Tests for the 402 payment flow."""
    
    @pytest.mark.asyncio
    async def test_normal_request_no_payment(self, mock_signer):
        """Test normal 200 response doesn't trigger payment."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response
            
            async with X402Client(signer=mock_signer) as client:
                response = await client.get("https://api.example.com/data")
                
                assert response.status_code == 200
                mock_signer.sign_payment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_402_without_header_no_retry(self, mock_signer):
        """Test 402 without payment requirements header doesn't retry."""
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 402
            mock_response.headers = {}  # No X-Payment-Requirements header
            mock_request.return_value = mock_response
            
            async with X402Client(signer=mock_signer) as client:
                response = await client.get("https://api.example.com/paid")
                
                assert response.status_code == 402
                mock_signer.sign_payment.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_402_exceeds_max_amount_no_payment(self, mock_signer):
        """Test 402 with amount exceeding max_amount doesn't pay."""
        requirements = PaymentRequirements(
            amount=10000,  # Exceeds max_amount
            recipient="0x0000000000000000000000000000000000000000",
            network=Network.BASE,
            resource="/api/data",
        )
        encoded = encode_requirements_header(requirements)
        
        with patch.object(httpx.AsyncClient, 'request') as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 402
            mock_response.headers = {X402_REQUIREMENTS_HEADER: encoded}
            mock_request.return_value = mock_response
            
            async with X402Client(signer=mock_signer, max_amount=1000) as client:
                response = await client.get("https://api.example.com/expensive")
                
                assert response.status_code == 402
                mock_signer.sign_payment.assert_not_called()
