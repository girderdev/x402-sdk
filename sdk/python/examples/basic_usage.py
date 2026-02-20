#!/usr/bin/env python3
"""
Basic x402 SDK Usage Example

This example demonstrates how to use the x402 Python SDK to:
1. Create a signer (using a local private key)
2. Configure an X402 client
3. Make requests to paid endpoints
4. Handle automatic payment flows
"""

import asyncio
from x402 import X402Client, LocalSigner


async def main():
    # 1. Create a signer
    # Option A: Generate a new random signer (for testing)
    signer = LocalSigner.generate()
    address = await signer.get_address()
    print(f"Generated wallet address: {address}")
    
    # Option B: From environment variable (recommended for production)
    # signer = LocalSigner.from_env("X402_PRIVATE_KEY")
    
    # Option C: From explicit private key (NOT recommended - use env vars)
    # signer = LocalSigner.from_private_key("0x...")

    # 2. Create the X402 client
    async with X402Client(
        signer=signer,
        auto_pay=True,                  # Automatically handle 402 responses
        max_amount=1_000_000,           # Max 1 USDC (6 decimals) per request
    ) as client:
        
        # 3. Make requests to paid endpoints
        # The client automatically:
        # - Detects 402 Payment Required responses
        # - Parses payment requirements from headers
        # - Signs payment payloads
        # - Retries with X-PAYMENT header
        
        try:
            # Example: Access a premium API endpoint
            response = await client.get(
                "https://api.example.com/premium/data",
                params={"query": "test"}
            )
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.json()}")
            
        except Exception as e:
            print(f"Request failed: {e}")


async def manual_payment_example():
    """
    Example showing manual payment handling (auto_pay=False)
    """
    from x402 import PaymentRequirements, PaymentPayload
    from x402.protocol import decode_requirements_header, encode_payment_header
    
    signer = LocalSigner.generate()
    
    async with X402Client(
        signer=signer,
        auto_pay=False,  # Don't auto-pay, handle manually
    ) as client:
        
        # First request - will get 402 if payment required
        response = await client.get("https://api.example.com/premium/data")
        
        if response.status_code == 402:
            # Parse payment requirements from response header
            requirements_header = response.headers.get("X-PAYMENT-REQUIREMENTS")
            if requirements_header:
                requirements = decode_requirements_header(requirements_header)
                print(f"Payment required:")
                print(f"  Amount: {requirements.max_amount_required}")
                print(f"  Recipient: {requirements.pay_to}")
                print(f"  Network: {requirements.network}")
                
                # Decide whether to pay (e.g., check budget, get user approval)
                should_pay = int(requirements.max_amount_required) <= 1_000_000
                
                if should_pay:
                    # Create and sign payment
                    payload = PaymentPayload(
                        amount=requirements.max_amount_required,
                        pay_to=requirements.pay_to,
                        nonce=client.get_nonce(),
                        expires_at=requirements.expires_at,
                        chain_id=requirements.network.chain_id,
                    )
                    
                    signature = await signer.sign_payment(payload)
                    
                    # Create signed payment
                    from x402 import SignedPayment
                    signed = SignedPayment(payload=payload, signature=signature)
                    
                    # Retry with payment header
                    payment_header = encode_payment_header(signed)
                    response = await client.get(
                        "https://api.example.com/premium/data",
                        headers={"X-PAYMENT": payment_header}
                    )
                    print(f"Paid response: {response.status_code}")


async def metered_api_example():
    """
    Example for metered/usage-based APIs where you pay per request
    """
    signer = LocalSigner.generate()
    
    async with X402Client(
        signer=signer,
        auto_pay=True,
        max_amount=100_000,  # Max $0.10 per request
    ) as client:
        
        # Make multiple metered requests
        endpoints = [
            "/api/v1/analyze",
            "/api/v1/translate", 
            "/api/v1/summarize",
        ]
        
        for endpoint in endpoints:
            try:
                response = await client.post(
                    f"https://api.example.com{endpoint}",
                    json={"text": "Hello world"}
                )
                print(f"{endpoint}: {response.status_code}")
            except Exception as e:
                print(f"{endpoint} failed: {e}")


if __name__ == "__main__":
    print("=== Basic Usage ===")
    asyncio.run(main())
    
    print("\n=== Manual Payment ===")
    asyncio.run(manual_payment_example())
    
    print("\n=== Metered API ===")
    asyncio.run(metered_api_example())
