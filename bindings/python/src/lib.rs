//! Python bindings for x402-core using PyO3
//!
//! This crate provides Python bindings to the Rust x402 core library.
//! It exposes the protocol encoding/decoding, signature verification,
//! and core types to Python.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use std::str::FromStr;

use alloy_primitives::{Address, U256};

use x402_core::{
    PaymentRequirements, PaymentPayload, SignedPayment, Network,
    encode_requirements_header, decode_requirements_header,
    encode_payment_header, decode_payment_header,
    verify_payment, X402Error,
};

/// Convert x402 Network to Python string
fn network_to_py(network: &Network) -> &'static str {
    match network {
        Network::Ethereum => "ethereum",
        Network::Base => "base",
        Network::BaseSepolia => "base_sepolia",
        Network::Arbitrum => "arbitrum",
        Network::Optimism => "optimism",
        Network::Polygon => "polygon",
    }
}

/// Convert Python string to x402 Network
fn py_to_network(network: &str) -> PyResult<Network> {
    match network.to_lowercase().as_str() {
        "ethereum" => Ok(Network::Ethereum),
        "base" => Ok(Network::Base),
        "base_sepolia" | "basesepolia" => Ok(Network::BaseSepolia),
        "arbitrum" => Ok(Network::Arbitrum),
        "optimism" => Ok(Network::Optimism),
        "polygon" => Ok(Network::Polygon),
        _ => Err(PyValueError::new_err(format!("Unknown network: {}", network))),
    }
}

/// Convert X402Error to PyErr
fn x402_err_to_py(e: X402Error) -> PyErr {
    match e {
        X402Error::InvalidHeader(msg) => PyValueError::new_err(format!("Invalid header: {}", msg)),
        X402Error::InvalidSignature(msg) => PyValueError::new_err(format!("Invalid signature: {}", msg)),
        X402Error::PaymentExpired => PyValueError::new_err("Payment expired"),
        X402Error::InsufficientAmount { required, provided } => {
            PyValueError::new_err(format!("Insufficient amount: required {}, got {}", required, provided))
        },
        X402Error::UnsupportedNetwork(msg) => PyValueError::new_err(format!("Unsupported network: {}", msg)),
        _ => PyRuntimeError::new_err(format!("x402 error: {}", e)),
    }
}

/// Python wrapper for PaymentRequirements
#[pyclass(name = "PaymentRequirements")]
#[derive(Clone)]
struct PyPaymentRequirements {
    inner: PaymentRequirements,
}

#[pymethods]
impl PyPaymentRequirements {
    #[new]
    #[pyo3(signature = (amount, recipient, network, resource, token=None, description=None, expires_at=None))]
    fn new(
        amount: u64,
        recipient: String,
        network: String,
        resource: String,
        token: Option<String>,
        description: Option<String>,
        expires_at: Option<u64>,
    ) -> PyResult<Self> {
        let recipient_addr = Address::from_str(&recipient)
            .map_err(|e| PyValueError::new_err(format!("Invalid recipient address: {}", e)))?;
        
        let token_addr = token.map(|t| {
            Address::from_str(&t)
        }).transpose()
            .map_err(|e| PyValueError::new_err(format!("Invalid token address: {}", e)))?;
        
        Ok(Self {
            inner: PaymentRequirements {
                amount: U256::from(amount),
                recipient: recipient_addr,
                network: py_to_network(&network)?,
                token: token_addr,
                description,
                expires_at,
                resource,
            }
        })
    }
    
    #[getter]
    fn amount(&self) -> u64 {
        self.inner.amount.try_into().unwrap_or(u64::MAX)
    }
    
    #[getter]
    fn recipient(&self) -> String {
        format!("{:?}", self.inner.recipient)
    }
    
    #[getter]
    fn network(&self) -> String {
        network_to_py(&self.inner.network).to_string()
    }
    
    #[getter]
    fn resource(&self) -> String {
        self.inner.resource.clone()
    }
    
    #[getter]
    fn description(&self) -> Option<String> {
        self.inner.description.clone()
    }
    
    #[getter]
    fn expires_at(&self) -> Option<u64> {
        self.inner.expires_at
    }
    
    #[getter]
    fn chain_id(&self) -> u64 {
        self.inner.network.chain_id()
    }
}

/// Python wrapper for PaymentPayload
#[pyclass(name = "PaymentPayload")]
#[derive(Clone)]
struct PyPaymentPayload {
    inner: PaymentPayload,
}

#[pymethods]
impl PyPaymentPayload {
    #[new]
    #[pyo3(signature = (amount, recipient, payer, chain_id, resource, nonce, expires_at, token=None))]
    fn new(
        amount: u64,
        recipient: String,
        payer: String,
        chain_id: u64,
        resource: String,
        nonce: u64,
        expires_at: u64,
        token: Option<String>,
    ) -> PyResult<Self> {
        let recipient_addr = Address::from_str(&recipient)
            .map_err(|e| PyValueError::new_err(format!("Invalid recipient address: {}", e)))?;
        
        let payer_addr = Address::from_str(&payer)
            .map_err(|e| PyValueError::new_err(format!("Invalid payer address: {}", e)))?;
        
        let token_addr = token.map(|t| {
            Address::from_str(&t)
        }).transpose()
            .map_err(|e| PyValueError::new_err(format!("Invalid token address: {}", e)))?;
        
        Ok(Self {
            inner: PaymentPayload {
                amount: U256::from(amount),
                recipient: recipient_addr,
                payer: payer_addr,
                chain_id,
                token: token_addr,
                resource,
                nonce,
                expires_at,
            }
        })
    }
    
    /// Get the message hash to be signed
    fn message_hash(&self) -> Vec<u8> {
        self.inner.message_hash().to_vec()
    }
    
    #[getter]
    fn amount(&self) -> u64 {
        self.inner.amount.try_into().unwrap_or(u64::MAX)
    }
    
    #[getter]
    fn recipient(&self) -> String {
        format!("{:?}", self.inner.recipient)
    }
    
    #[getter]
    fn payer(&self) -> String {
        format!("{:?}", self.inner.payer)
    }
    
    #[getter]
    fn chain_id(&self) -> u64 {
        self.inner.chain_id
    }
    
    #[getter]
    fn resource(&self) -> String {
        self.inner.resource.clone()
    }
    
    #[getter]
    fn nonce(&self) -> u64 {
        self.inner.nonce
    }
    
    #[getter]
    fn expires_at(&self) -> u64 {
        self.inner.expires_at
    }
}

/// Encode payment requirements to a base64 header value
#[pyfunction]
fn encode_requirements(requirements: &PyPaymentRequirements) -> PyResult<String> {
    encode_requirements_header(&requirements.inner)
        .map_err(x402_err_to_py)
}

/// Decode payment requirements from a base64 header value
#[pyfunction]
fn decode_requirements(header: &str) -> PyResult<PyPaymentRequirements> {
    let inner = decode_requirements_header(header)
        .map_err(x402_err_to_py)?;
    Ok(PyPaymentRequirements { inner })
}

/// Encode a signed payment to a base64 header value
#[pyfunction]
fn encode_payment(payload: &PyPaymentPayload, signature: Vec<u8>) -> PyResult<String> {
    let signed = SignedPayment {
        payment: payload.inner.clone(),
        signature,
    };
    encode_payment_header(&signed)
        .map_err(x402_err_to_py)
}

/// Decode a signed payment from a base64 header value
/// Returns a tuple of (PaymentPayload, signature_bytes)
#[pyfunction]
fn decode_payment(header: &str) -> PyResult<(PyPaymentPayload, Vec<u8>)> {
    let signed = decode_payment_header(header)
        .map_err(x402_err_to_py)?;
    Ok((
        PyPaymentPayload { inner: signed.payment },
        signed.signature,
    ))
}

/// Verify a signed payment against requirements
/// Returns the verified payer address
#[pyfunction]
fn verify_signed_payment(payment_header: &str, requirements: &PyPaymentRequirements) -> PyResult<String> {
    let signed = decode_payment_header(payment_header)
        .map_err(x402_err_to_py)?;
    
    let payer = verify_payment(&signed, &requirements.inner)
        .map_err(x402_err_to_py)?;
    
    Ok(format!("{:?}", payer))
}

/// Get the chain ID for a network name
#[pyfunction]
fn get_chain_id(network: &str) -> PyResult<u64> {
    let net = py_to_network(network)?;
    Ok(net.chain_id())
}

/// Get the network name for a chain ID
#[pyfunction]
fn get_network_name(chain_id: u64) -> PyResult<String> {
    Network::from_chain_id(chain_id)
        .map(|n| network_to_py(&n).to_string())
        .ok_or_else(|| PyValueError::new_err(format!("Unknown chain ID: {}", chain_id)))
}

/// x402 native Python module
#[pymodule]
fn x402_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Types
    m.add_class::<PyPaymentRequirements>()?;
    m.add_class::<PyPaymentPayload>()?;
    
    // Protocol functions
    m.add_function(wrap_pyfunction!(encode_requirements, m)?)?;
    m.add_function(wrap_pyfunction!(decode_requirements, m)?)?;
    m.add_function(wrap_pyfunction!(encode_payment, m)?)?;
    m.add_function(wrap_pyfunction!(decode_payment, m)?)?;
    
    // Verification
    m.add_function(wrap_pyfunction!(verify_signed_payment, m)?)?;
    
    // Network utilities
    m.add_function(wrap_pyfunction!(get_chain_id, m)?)?;
    m.add_function(wrap_pyfunction!(get_network_name, m)?)?;
    
    // Constants
    m.add("X402_REQUIREMENTS_HEADER", x402_core::X402_REQUIREMENTS_HEADER)?;
    m.add("X402_PAYMENT_HEADER", x402_core::X402_PAYMENT_HEADER)?;
    
    Ok(())
}
