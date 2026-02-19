//! Core types for x402 payments

use alloy_primitives::{Address, U256};
use serde::{Deserialize, Serialize};

/// Supported blockchain networks
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Network {
    /// Ethereum Mainnet
    Ethereum,
    /// Base Mainnet
    Base,
    /// Base Sepolia Testnet
    BaseSepolia,
    /// Arbitrum One
    Arbitrum,
    /// Optimism
    Optimism,
    /// Polygon
    Polygon,
}

impl Network {
    pub fn chain_id(&self) -> u64 {
        match self {
            Network::Ethereum => 1,
            Network::Base => 8453,
            Network::BaseSepolia => 84532,
            Network::Arbitrum => 42161,
            Network::Optimism => 10,
            Network::Polygon => 137,
        }
    }

    pub fn from_chain_id(chain_id: u64) -> Option<Self> {
        match chain_id {
            1 => Some(Network::Ethereum),
            8453 => Some(Network::Base),
            84532 => Some(Network::BaseSepolia),
            42161 => Some(Network::Arbitrum),
            10 => Some(Network::Optimism),
            137 => Some(Network::Polygon),
            _ => None,
        }
    }
}

/// Payment requirements returned in 402 response
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaymentRequirements {
    /// Amount in smallest unit (wei, satoshi, etc.)
    pub amount: U256,
    /// Recipient address
    pub recipient: Address,
    /// Network to pay on
    pub network: Network,
    /// Token address (None = native token like ETH)
    pub token: Option<Address>,
    /// Human-readable description
    pub description: Option<String>,
    /// Payment expiry (unix timestamp)
    pub expires_at: Option<u64>,
    /// Unique resource identifier
    pub resource: String,
}

/// Signed payment submitted by client
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SignedPayment {
    /// Payment details
    pub payment: PaymentPayload,
    /// ECDSA signature (65 bytes: r + s + v)
    pub signature: Vec<u8>,
}

/// Payment payload to be signed
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PaymentPayload {
    /// Amount in smallest unit
    pub amount: U256,
    /// Recipient address
    pub recipient: Address,
    /// Payer address
    pub payer: Address,
    /// Network chain ID
    pub chain_id: u64,
    /// Token address (None = native token)
    pub token: Option<Address>,
    /// Resource being paid for
    pub resource: String,
    /// Nonce for replay protection
    pub nonce: u64,
    /// Expiry timestamp
    pub expires_at: u64,
}

impl PaymentPayload {
    /// Create the message hash to be signed (EIP-712 style)
    pub fn message_hash(&self) -> [u8; 32] {
        use alloy_primitives::keccak256;
        
        // Simplified hashing - in production, use full EIP-712 typed data
        let message = format!(
            "x402 Payment\nAmount: {}\nRecipient: {}\nPayer: {}\nChainId: {}\nResource: {}\nNonce: {}\nExpires: {}",
            self.amount,
            self.recipient,
            self.payer,
            self.chain_id,
            self.resource,
            self.nonce,
            self.expires_at
        );
        
        *keccak256(message.as_bytes())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_network_chain_id() {
        assert_eq!(Network::Base.chain_id(), 8453);
        assert_eq!(Network::from_chain_id(8453), Some(Network::Base));
    }

    #[test]
    fn test_payment_message_hash() {
        let payload = PaymentPayload {
            amount: U256::from(1000000),
            recipient: Address::ZERO,
            payer: Address::ZERO,
            chain_id: 8453,
            token: None,
            resource: "https://api.example.com/data".to_string(),
            nonce: 1,
            expires_at: 1700000000,
        };
        
        let hash = payload.message_hash();
        assert_eq!(hash.len(), 32);
    }
}
