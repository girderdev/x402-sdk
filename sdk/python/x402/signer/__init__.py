"""Signer implementations for x402.

The signer interface allows pluggable signing backends:
- LocalSigner: For development (loads key from env/file)
- AWSKMSSigner: AWS Key Management Service
- VaultSigner: HashiCorp Vault Transit
- Custom: Implement the Signer protocol
"""

from x402.signer.base import Signer
from x402.signer.local import LocalSigner
from x402.signer.aws_kms import AWSKMSSigner

__all__ = [
    "Signer",
    "LocalSigner",
    "AWSKMSSigner",
]
