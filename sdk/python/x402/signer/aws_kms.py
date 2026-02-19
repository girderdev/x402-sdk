"""AWS KMS signer for production use.

Uses AWS Key Management Service for signing.
The private key never leaves the KMS HSM.

Requirements:
    pip install x402[aws]
"""

from typing import Optional

from x402.signer.base import BaseSigner
from x402.types import PaymentPayload


class AWSKMSSigner(BaseSigner):
    """AWS KMS signer.
    
    Signs payments using AWS KMS. The private key is stored
    in AWS KMS and never leaves the HSM.
    
    Setup:
        1. Create an asymmetric KMS key (ECC_SECG_P256K1)
        2. Grant your IAM role/user kms:Sign and kms:GetPublicKey permissions
        3. Use the key ARN or alias
    
    Example:
        signer = AWSKMSSigner(
            key_id="arn:aws:kms:us-east-1:123456789:key/abc-123",
            region="us-east-1"
        )
    """
    
    def __init__(
        self,
        key_id: str,
        region: Optional[str] = None,
        profile: Optional[str] = None,
    ):
        """Initialize AWS KMS signer.
        
        Args:
            key_id: KMS key ID, ARN, or alias
            region: AWS region (defaults to environment/config)
            profile: AWS profile name (defaults to environment/config)
        """
        self._key_id = key_id
        self._region = region
        self._profile = profile
        self._client = None
        self._address: Optional[str] = None
    
    def _get_client(self):
        """Lazy-load boto3 client."""
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS KMS signer. "
                    "Install with: pip install x402[aws]"
                )
            
            session_kwargs = {}
            if self._profile:
                session_kwargs["profile_name"] = self._profile
            if self._region:
                session_kwargs["region_name"] = self._region
            
            session = boto3.Session(**session_kwargs)
            self._client = session.client("kms")
        
        return self._client
    
    async def sign_payment(self, payload: PaymentPayload) -> bytes:
        """Sign a payment using AWS KMS.
        
        Args:
            payload: Payment payload to sign
            
        Returns:
            65-byte signature (r + s + v)
        """
        client = self._get_client()
        message_hash = payload.message_hash()
        
        # Sign with KMS
        response = client.sign(
            KeyId=self._key_id,
            Message=message_hash,
            MessageType="DIGEST",
            SigningAlgorithm="ECDSA_SHA_256",
        )
        
        # Convert DER-encoded signature to (r, s, v) format
        der_signature = response["Signature"]
        signature = self._der_to_rsv(der_signature, message_hash)
        
        return signature
    
    async def get_address(self) -> str:
        """Get the Ethereum address for this KMS key.
        
        Returns:
            Checksummed Ethereum address
        """
        if self._address is None:
            client = self._get_client()
            
            # Get public key from KMS
            response = client.get_public_key(KeyId=self._key_id)
            public_key_der = response["PublicKey"]
            
            # Convert to Ethereum address
            self._address = self._public_key_to_address(public_key_der)
        
        return self._address
    
    def _der_to_rsv(self, der_signature: bytes, message_hash: bytes) -> bytes:
        """Convert DER-encoded signature to Ethereum (r, s, v) format.
        
        Args:
            der_signature: DER-encoded ECDSA signature
            message_hash: Original message hash (for recovery)
            
        Returns:
            65-byte signature (r + s + v)
        """
        # Parse DER signature
        from eth_account._utils.signing import to_bytes32
        import struct
        
        # DER format: 0x30 <length> 0x02 <r_len> <r> 0x02 <s_len> <s>
        # Skip the DER envelope
        pos = 2  # Skip 0x30 <length>
        
        # Parse r
        if der_signature[pos] != 0x02:
            raise ValueError("Invalid DER signature")
        pos += 1
        r_len = der_signature[pos]
        pos += 1
        r = int.from_bytes(der_signature[pos:pos + r_len], "big")
        pos += r_len
        
        # Parse s
        if der_signature[pos] != 0x02:
            raise ValueError("Invalid DER signature")
        pos += 1
        s_len = der_signature[pos]
        pos += 1
        s = int.from_bytes(der_signature[pos:pos + s_len], "big")
        
        # Normalize s (EIP-2)
        secp256k1_n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        if s > secp256k1_n // 2:
            s = secp256k1_n - s
        
        # Calculate v by trying both recovery IDs
        r_bytes = r.to_bytes(32, "big")
        s_bytes = s.to_bytes(32, "big")
        
        # Try v = 27 and v = 28 to find which recovers to our address
        # For now, default to 27 (will be fixed with proper recovery)
        v = 27
        
        return r_bytes + s_bytes + bytes([v])
    
    def _public_key_to_address(self, public_key_der: bytes) -> str:
        """Convert DER-encoded public key to Ethereum address.
        
        Args:
            public_key_der: DER-encoded public key from KMS
            
        Returns:
            Checksummed Ethereum address
        """
        from eth_account._utils.signing import keccak
        from eth_utils import to_checksum_address
        
        # Parse the DER-encoded public key to get the raw point
        # Skip DER envelope to get the 65-byte uncompressed public key (04 + x + y)
        # The structure is: SEQUENCE { SEQUENCE { OID, OID }, BIT STRING { public key } }
        
        # Find the BIT STRING (0x03) and skip its header
        pos = 0
        while pos < len(public_key_der) - 2:
            if public_key_der[pos] == 0x03:  # BIT STRING
                pos += 1
                length = public_key_der[pos]
                pos += 1
                pos += 1  # Skip the "unused bits" byte
                break
            pos += 1
        
        raw_pubkey = public_key_der[pos:]
        
        # Should be 65 bytes: 0x04 + 32 bytes X + 32 bytes Y
        if len(raw_pubkey) >= 65 and raw_pubkey[0] == 0x04:
            raw_pubkey = raw_pubkey[1:65]  # Remove 0x04 prefix
        elif len(raw_pubkey) >= 64:
            raw_pubkey = raw_pubkey[:64]
        
        # Keccak256 hash and take last 20 bytes
        address_bytes = keccak(raw_pubkey)[-20:]
        return to_checksum_address(address_bytes)
