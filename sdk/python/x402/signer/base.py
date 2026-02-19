"""Base signer interface."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from x402.types import PaymentPayload


@runtime_checkable
class Signer(Protocol):
    """Protocol for x402 payment signers.
    
    Implement this interface to use custom signing backends
    (KMS, HSM, hardware wallets, etc.)
    
    The private key should NEVER be exposed through this interface.
    Only the signing operation and address retrieval are exposed.
    """
    
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        """Sign a payment payload.
        
        Args:
            payload: The payment payload to sign
            
        Returns:
            65-byte ECDSA signature (r + s + v)
        """
        ...
    
    async def get_address(self) -> str:
        """Get the signer's address.
        
        Returns:
            Checksummed Ethereum address
        """
        ...


class BaseSigner(ABC):
    """Abstract base class for signers."""
    
    @abstractmethod
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        """Sign a payment payload."""
        pass
    
    @abstractmethod
    async def get_address(self) -> str:
        """Get the signer's address."""
        pass
