"""x402 HTTP client with automatic payment handling."""

import time
from typing import Any, Optional, Dict, Union

import httpx

from x402.types import PaymentRequirements, PaymentPayload, SignedPayment, Network
from x402.protocol import (
    X402_REQUIREMENTS_HEADER,
    X402_PAYMENT_HEADER,
    decode_requirements_header,
    encode_payment_header,
)
from x402.signer.base import Signer


class X402Client:
    """HTTP client that automatically handles x402 payment flows.
    
    When a request receives a 402 Payment Required response,
    the client will:
    1. Parse the payment requirements
    2. Sign the payment using the configured signer
    3. Retry the request with the payment header
    
    Example:
        signer = LocalSigner.from_env("X402_PRIVATE_KEY")
        client = X402Client(signer=signer)
        
        # Automatic payment handling
        response = await client.get("https://api.example.com/premium")
    """
    
    def __init__(
        self,
        signer: Signer,
        *,
        max_amount: Optional[int] = None,
        auto_pay: bool = True,
        timeout: float = 30.0,
        base_url: Optional[str] = None,
    ):
        """Initialize x402 client.
        
        Args:
            signer: Signer instance for signing payments
            max_amount: Maximum amount to auto-pay (in wei). None = no limit
            auto_pay: Whether to automatically pay 402 responses
            timeout: Request timeout in seconds
            base_url: Optional base URL for all requests
        """
        self._signer = signer
        self._max_amount = max_amount
        self._auto_pay = auto_pay
        self._nonce = int(time.time() * 1000)  # Simple incrementing nonce
        
        self._client = httpx.AsyncClient(
            timeout=timeout,
            base_url=base_url or "",
        )
    
    async def __aenter__(self) -> "X402Client":
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with automatic 402 handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Optional headers
            **kwargs: Additional arguments passed to httpx
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: On HTTP errors (after payment attempt if 402)
        """
        headers = dict(headers or {})
        
        # Make initial request
        response = await self._client.request(method, url, headers=headers, **kwargs)
        
        # Handle 402 Payment Required
        if response.status_code == 402 and self._auto_pay:
            payment_header = await self._handle_402(response, url)
            
            if payment_header:
                # Retry with payment
                headers[X402_PAYMENT_HEADER] = payment_header
                response = await self._client.request(method, url, headers=headers, **kwargs)
        
        return response
    
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    async def _handle_402(self, response: httpx.Response, url: str) -> Optional[str]:
        """Handle a 402 response by signing a payment.
        
        Args:
            response: The 402 response
            url: Original request URL
            
        Returns:
            Encoded payment header, or None if payment was rejected
        """
        # Get payment requirements from header
        requirements_header = response.headers.get(X402_REQUIREMENTS_HEADER)
        if not requirements_header:
            return None
        
        try:
            requirements = decode_requirements_header(requirements_header)
        except ValueError:
            return None
        
        # Check max amount
        if self._max_amount is not None and requirements.amount > self._max_amount:
            return None
        
        # Create payment payload
        payer_address = await self._signer.get_address()
        
        # Get chain ID from network
        if isinstance(requirements.network, Network):
            chain_id = requirements.network.chain_id
        else:
            chain_id = _get_chain_id(requirements.network)
        
        payload = PaymentPayload(
            amount=requirements.amount,
            recipient=requirements.recipient,
            payer=payer_address,
            chain_id=chain_id,
            token=requirements.token,
            resource=requirements.resource,
            nonce=self._get_nonce(),
            expires_at=requirements.expires_at or (int(time.time()) + 300),  # 5 min default
        )
        
        # Sign the payment
        signature = await self._signer.sign_payment(payload)
        
        signed_payment = SignedPayment(payment=payload, signature=signature)
        
        return encode_payment_header(signed_payment)
    
    def _get_nonce(self) -> int:
        """Get next nonce value."""
        self._nonce += 1
        return self._nonce


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
