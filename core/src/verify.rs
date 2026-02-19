//! Signature verification for x402 payments

use crate::{SignedPayment, PaymentRequirements, X402Error, Result};
use alloy_primitives::Address;
use k256::ecdsa::{RecoveryId, Signature, VerifyingKey};

/// Verify a signed payment against requirements
/// 
/// Checks:
/// 1. Signature is valid and recovers to payer address
/// 2. Amount meets requirements
/// 3. Recipient matches
/// 4. Payment not expired
/// 5. Network matches
pub fn verify_payment(
    payment: &SignedPayment,
    requirements: &PaymentRequirements,
) -> Result<Address> {
    // Check expiry
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    if payment.payment.expires_at < now {
        return Err(X402Error::PaymentExpired);
    }

    // Check amount (convert U256 to u64 for comparison - simplified)
    let required_amount: u64 = requirements.amount.try_into()
        .unwrap_or(u64::MAX);
    let provided_amount: u64 = payment.payment.amount.try_into()
        .unwrap_or(0);
    
    if provided_amount < required_amount {
        return Err(X402Error::InsufficientAmount {
            required: required_amount,
            provided: provided_amount,
        });
    }

    // Check recipient
    if payment.payment.recipient != requirements.recipient {
        return Err(X402Error::InvalidSignature(
            "recipient mismatch".to_string()
        ));
    }

    // Check network
    if payment.payment.chain_id != requirements.network.chain_id() {
        return Err(X402Error::UnsupportedNetwork(
            format!("expected chain {}, got {}", 
                requirements.network.chain_id(), 
                payment.payment.chain_id)
        ));
    }

    // Verify signature and recover payer address
    let recovered_address = recover_signer(payment)?;
    
    if recovered_address != payment.payment.payer {
        return Err(X402Error::InvalidSignature(
            "recovered address does not match payer".to_string()
        ));
    }

    Ok(recovered_address)
}

/// Recover the signer address from a signed payment
pub fn recover_signer(payment: &SignedPayment) -> Result<Address> {
    if payment.signature.len() != 65 {
        return Err(X402Error::InvalidSignature(
            format!("signature must be 65 bytes, got {}", payment.signature.len())
        ));
    }

    let message_hash = payment.payment.message_hash();
    
    // Parse signature components
    let r_s = &payment.signature[..64];
    let v = payment.signature[64];
    
    // Recovery ID: v is either 27/28 (legacy) or 0/1
    let recovery_id = if v >= 27 {
        RecoveryId::try_from(v - 27)
    } else {
        RecoveryId::try_from(v)
    }.map_err(|_| X402Error::InvalidSignature("invalid recovery id".to_string()))?;

    let signature = Signature::from_slice(r_s)
        .map_err(|e| X402Error::InvalidSignature(e.to_string()))?;

    let verifying_key = VerifyingKey::recover_from_prehash(&message_hash, &signature, recovery_id)
        .map_err(|e| X402Error::InvalidSignature(e.to_string()))?;

    // Convert public key to Ethereum address
    let public_key_bytes = verifying_key.to_encoded_point(false);
    let public_key_hash = alloy_primitives::keccak256(&public_key_bytes.as_bytes()[1..]);
    let address = Address::from_slice(&public_key_hash[12..]);

    Ok(address)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_invalid_signature_length() {
        use crate::{PaymentPayload, SignedPayment};
        use alloy_primitives::U256;

        let payment = SignedPayment {
            payment: PaymentPayload {
                amount: U256::from(1000),
                recipient: Address::ZERO,
                payer: Address::ZERO,
                chain_id: 8453,
                token: None,
                resource: "/test".to_string(),
                nonce: 1,
                expires_at: u64::MAX,
            },
            signature: vec![0u8; 64], // Wrong length
        };

        let result = recover_signer(&payment);
        assert!(result.is_err());
    }
}
