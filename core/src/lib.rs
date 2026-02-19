//! x402-core: Core library for the x402 Payment Protocol
//!
//! This crate provides:
//! - Payment types and structures
//! - x402 header encoding/decoding
//! - Signature verification
//!
//! Note: This crate does NOT perform signing. Signing is delegated to
//! external signers (KMS, hardware wallets, browser wallets, etc.)

pub mod types;
pub mod protocol;
pub mod verify;
pub mod error;

pub use types::*;
pub use protocol::*;
pub use verify::*;
pub use error::*;
