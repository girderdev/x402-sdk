"""Core types for x402 payments."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from eth_typing import ChecksumAddress


class Network(str, Enum):
    """Supported blockchain networks."""
    
    ETHEREUM = "ethereum"
    BASE = "base"
    BASE_SEPOLIA = "base_sepolia"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    POLYGON = "polygon"

    @property
    def chain_id(self) -> int:
        """Get the chain ID for this network."""
        chain_ids = {
            Network.ETHEREUM: 1,
            Network.BASE: 8453,
            Network.BASE_SEPOLIA: 84532,
            Network.ARBITRUM: 42161,
            Network.OPTIMISM: 10,
            Network.POLYGON: 137,
        }
        return chain_ids[self]

    @classmethod
    def from_chain_id(cls, chain_id: int) -> Optional["Network"]:
        """Get network from chain ID."""
        for network in cls:
            if network.chain_id == chain_id:
                return network
        return None


class PaymentRequirements(BaseModel):
    """Payment requirements returned in 402 response."""
    
    amount: int = Field(..., description="Amount in smallest unit (wei)")
    recipient: str = Field(..., description="Recipient address")
    network: Network = Field(..., description="Network to pay on")
    token: Optional[str] = Field(None, description="Token address (None = native)")
    description: Optional[str] = Field(None, description="Human-readable description")
    expires_at: Optional[int] = Field(None, description="Payment expiry (unix timestamp)")
    resource: str = Field(..., description="Resource being paid for")

    model_config = ConfigDict(use_enum_values=True)


class PaymentPayload(BaseModel):
    """Payment payload to be signed."""
    
    amount: int = Field(..., description="Amount in smallest unit")
    recipient: str = Field(..., description="Recipient address")
    payer: str = Field(..., description="Payer address")
    chain_id: int = Field(..., description="Network chain ID")
    token: Optional[str] = Field(None, description="Token address")
    resource: str = Field(..., description="Resource being paid for")
    nonce: int = Field(..., description="Nonce for replay protection")
    expires_at: int = Field(..., description="Expiry timestamp")

    def message_hash(self) -> bytes:
        """Create the message hash to be signed."""
        from eth_hash.auto import keccak
        
        # Simplified hashing - matches Rust core
        message = (
            f"x402 Payment\n"
            f"Amount: {self.amount}\n"
            f"Recipient: {self.recipient}\n"
            f"Payer: {self.payer}\n"
            f"ChainId: {self.chain_id}\n"
            f"Resource: {self.resource}\n"
            f"Nonce: {self.nonce}\n"
            f"Expires: {self.expires_at}"
        )
        
        return keccak(message.encode())


class SignedPayment(BaseModel):
    """Signed payment submitted by client."""
    
    payment: PaymentPayload
    signature: bytes

    model_config = ConfigDict(arbitrary_types_allowed=True)
