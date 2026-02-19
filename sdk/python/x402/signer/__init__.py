"""Signer implementations for x402.

The signer interface allows pluggable signing backends:
- LocalSigner: For development (loads key from env/file)
- AWSKMSSigner: AWS Key Management Service
- VaultSigner: HashiCorp Vault Transit
- Custom: Implement the Signer protocol
"""

from x402.signer.base import Signer
from x402.signer.local import LocalSigner

__all__ = [
    "Signer",
    "LocalSigner",
]
