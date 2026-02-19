//! x402 protocol header encoding/decoding

use crate::{PaymentRequirements, SignedPayment, X402Error, Result};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};

/// Header name for payment requirements (server → client)
pub const X402_REQUIREMENTS_HEADER: &str = "X-Payment-Requirements";

/// Header name for signed payment (client → server)
pub const X402_PAYMENT_HEADER: &str = "X-Payment";

/// Encode payment requirements to header value
/// 
/// # Example
/// ```
/// use x402_core::{PaymentRequirements, encode_requirements_header, Network};
/// use alloy_primitives::{Address, U256};
/// 
/// let requirements = PaymentRequirements {
///     amount: U256::from(1000000),
///     recipient: Address::ZERO,
///     network: Network::Base,
///     token: None,
///     description: Some("API access".to_string()),
///     expires_at: None,
///     resource: "/api/data".to_string(),
/// };
/// 
/// let header = encode_requirements_header(&requirements).unwrap();
/// ```
pub fn encode_requirements_header(requirements: &PaymentRequirements) -> Result<String> {
    let json = serde_json::to_string(requirements)
        .map_err(|e| X402Error::EncodingError(e.to_string()))?;
    Ok(BASE64.encode(json.as_bytes()))
}

/// Decode payment requirements from header value
pub fn decode_requirements_header(header: &str) -> Result<PaymentRequirements> {
    let bytes = BASE64.decode(header)
        .map_err(|e| X402Error::InvalidHeader(format!("base64 decode failed: {}", e)))?;
    
    let json = String::from_utf8(bytes)
        .map_err(|e| X402Error::InvalidHeader(format!("invalid UTF-8: {}", e)))?;
    
    serde_json::from_str(&json)
        .map_err(|e| X402Error::InvalidHeader(format!("JSON parse failed: {}", e)))
}

/// Encode signed payment to header value
pub fn encode_payment_header(payment: &SignedPayment) -> Result<String> {
    let json = serde_json::to_string(payment)
        .map_err(|e| X402Error::EncodingError(e.to_string()))?;
    Ok(BASE64.encode(json.as_bytes()))
}

/// Decode signed payment from header value
pub fn decode_payment_header(header: &str) -> Result<SignedPayment> {
    let bytes = BASE64.decode(header)
        .map_err(|e| X402Error::InvalidHeader(format!("base64 decode failed: {}", e)))?;
    
    let json = String::from_utf8(bytes)
        .map_err(|e| X402Error::InvalidHeader(format!("invalid UTF-8: {}", e)))?;
    
    serde_json::from_str(&json)
        .map_err(|e| X402Error::InvalidHeader(format!("JSON parse failed: {}", e)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Network;
    use alloy_primitives::{Address, U256};

    #[test]
    fn test_requirements_roundtrip() {
        let requirements = PaymentRequirements {
            amount: U256::from(1000000),
            recipient: Address::ZERO,
            network: Network::Base,
            token: None,
            description: Some("Test payment".to_string()),
            expires_at: Some(1700000000),
            resource: "/api/test".to_string(),
        };

        let encoded = encode_requirements_header(&requirements).unwrap();
        let decoded = decode_requirements_header(&encoded).unwrap();

        assert_eq!(decoded.amount, requirements.amount);
        assert_eq!(decoded.recipient, requirements.recipient);
        assert_eq!(decoded.resource, requirements.resource);
    }
}
