"""Local signer for development and testing.

WARNING: This signer loads private keys into memory.
Use KMS/HSM signers in production!
"""

import os
from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct

from x402.signer.base import BaseSigner
from x402.types import PaymentPayload


class LocalSigner(BaseSigner):
    """Local signer using eth-account.
    
    WARNING: Only use for development/testing!
    Private keys are loaded into memory.
    
    For production, use:
    - AWSKMSSigner
    - VaultSigner  
    - Or implement your own Signer
    """
    
    def __init__(self, account: Account):
        """Initialize with an eth-account Account.
        
        Args:
            account: eth-account Account instance
        """
        self._account = account
    
    @classmethod
    def from_env(cls, env_var: str = "X402_PRIVATE_KEY") -> "LocalSigner":
        """Create signer from environment variable.
        
        Args:
            env_var: Name of environment variable containing private key
            
        Returns:
            LocalSigner instance
            
        Raises:
            ValueError: If environment variable is not set
        """
        private_key = os.environ.get(env_var)
        if not private_key:
            raise ValueError(
                f"Environment variable {env_var} is not set. "
                f"Set it to your private key (0x-prefixed hex string)."
            )
        return cls.from_private_key(private_key)
    
    @classmethod
    def from_private_key(cls, private_key: str) -> "LocalSigner":
        """Create signer from private key string.
        
        WARNING: Avoid using this in production!
        
        Args:
            private_key: Private key as 0x-prefixed hex string
            
        Returns:
            LocalSigner instance
        """
        account = Account.from_key(private_key)
        return cls(account)
    
    @classmethod
    def from_keystore(cls, path: str, password: str) -> "LocalSigner":
        """Create signer from encrypted keystore file.
        
        Args:
            path: Path to keystore JSON file
            password: Password to decrypt keystore
            
        Returns:
            LocalSigner instance
        """
        with open(path) as f:
            keystore = f.read()
        private_key = Account.decrypt(keystore, password)
        return cls(Account.from_key(private_key))
    
    @classmethod
    def generate(cls) -> "LocalSigner":
        """Generate a new random signer.
        
        Useful for testing.
        
        Returns:
            LocalSigner instance with new random key
        """
        account = Account.create()
        return cls(account)
    
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        """Sign a payment payload.
        
        Args:
            payload: Payment payload to sign
            
        Returns:
            65-byte signature (r + s + v)
        """
        message_hash = payload.message_hash()
        signed = self._account.sign_message(encode_defunct(primitive=message_hash))
        return signed.signature
    
    async def get_address(self) -> str:
        """Get the signer's address.
        
        Returns:
            Checksummed Ethereum address
        """
        return self._account.address
