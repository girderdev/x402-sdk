//! Error types for x402-core

use thiserror::Error;

#[derive(Error, Debug)]
pub enum X402Error {
    #[error("Invalid x402 header format: {0}")]
    InvalidHeader(String),

    #[error("Invalid signature: {0}")]
    InvalidSignature(String),

    #[error("Invalid address: {0}")]
    InvalidAddress(String),

    #[error("Encoding error: {0}")]
    EncodingError(String),

    #[error("Payment expired")]
    PaymentExpired,

    #[error("Insufficient amount: required {required}, got {provided}")]
    InsufficientAmount { required: u64, provided: u64 },

    #[error("Unsupported network: {0}")]
    UnsupportedNetwork(String),
}

pub type Result<T> = std::result::Result<T, X402Error>;
