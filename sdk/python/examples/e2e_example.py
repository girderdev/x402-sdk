#!/usr/bin/env python3
"""
End-to-End x402 Example with Mock Server

This example runs a complete flow:
1. Starts a mock server that requires x402 payments
2. Client makes requests and handles payments automatically

Run with: python examples/e2e_example.py
"""

import asyncio
import json
import time
from aiohttp import web
from x402 import X402Client, LocalSigner, Network, PaymentRequirements
from x402.protocol import encode_requirements_header
from x402.verify import verify_payment


# ============================================================================
# MOCK SERVER (simulates a paid API)
# ============================================================================

# Server's wallet address (would receive payments in production)
SERVER_WALLET = "0x1234567890123456789012345678901234567890"

# Price per request in USDC (6 decimals) - $0.001
PRICE_PER_REQUEST = 1000


async def premium_endpoint(request: web.Request) -> web.Response:
    """A premium endpoint that requires x402 payment."""
    
    # Check for payment header (case-insensitive lookup)
    payment_header = request.headers.get("X-Payment") or request.headers.get("x-payment")
    
    if not payment_header:
        # No payment - return 402 with requirements
        requirements = PaymentRequirements(
            amount=PRICE_PER_REQUEST,
            network=Network.BASE_SEPOLIA,
            resource=str(request.url),
            description="Premium API access",
            recipient=SERVER_WALLET,
            expires_at=int(time.time()) + 300,  # 5 minutes
        )
        
        return web.Response(
            status=402,
            headers={
                "X-PAYMENT-REQUIREMENTS": encode_requirements_header(requirements),
            },
            text="Payment Required",
        )
    
    # Verify the payment
    try:
        # Create requirements for verification
        requirements = PaymentRequirements(
            amount=PRICE_PER_REQUEST,
            network=Network.BASE_SEPOLIA,
            resource=str(request.url),
            description="Premium API access", 
            recipient=SERVER_WALLET,
            expires_at=int(time.time()) + 300,
        )
        
        # Verify payment (checks signature, amount, expiry, recipient)
        # verify_payment takes the raw header string and decodes internally
        payer_address = verify_payment(payment_header, requirements)
        
        # Payment valid - return premium content
        return web.json_response({
            "status": "success",
            "message": "Access granted!",
            "data": {
                "premium_content": "This is valuable paid content",
                "timestamp": time.time(),
                "payer": payer_address,
            }
        })
        
    except Exception as e:
        return web.json_response(
            {"error": f"Payment verification failed: {str(e)}"},
            status=400,
        )


async def health_endpoint(request: web.Request) -> web.Response:
    """Free health check endpoint."""
    return web.json_response({"status": "healthy"})


def create_server_app() -> web.Application:
    """Create the mock server application."""
    app = web.Application()
    app.router.add_get("/health", health_endpoint)
    app.router.add_get("/api/premium", premium_endpoint)
    app.router.add_post("/api/premium", premium_endpoint)
    return app


# ============================================================================
# CLIENT CODE
# ============================================================================

async def run_client(base_url: str):
    """Run the x402 client against the mock server."""
    
    print("\n" + "="*60)
    print("CLIENT: Starting x402 client")
    print("="*60)
    
    # Generate a test signer
    signer = LocalSigner.generate()
    address = await signer.get_address()
    print(f"Client wallet: {address}")
    
    async with X402Client(
        signer=signer,
        auto_pay=True,
        max_amount=10_000,  # Max $0.01 per request
    ) as client:
        
        # Test 1: Free endpoint (health check)
        print("\n--- Test 1: Free endpoint ---")
        response = await client.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.json()}")
        
        # Test 2: Premium endpoint (requires payment)
        print("\n--- Test 2: Premium endpoint (auto-pay) ---")
        response = await client.get(f"{base_url}/api/premium")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Body: {response.json()}")
        else:
            print(f"Error: {response.text}")
        
        # Test 3: Multiple paid requests
        print("\n--- Test 3: Multiple paid requests ---")
        for i in range(3):
            response = await client.get(f"{base_url}/api/premium")
            status = "✓" if response.status_code == 200 else "✗"
            print(f"Request {i+1}: {status} (status={response.status_code})")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the end-to-end example."""
    
    print("="*60)
    print("x402 End-to-End Example")
    print("="*60)
    
    # Start server
    app = create_server_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "localhost", 8402)
    await site.start()
    print("SERVER: Mock x402 server running on http://localhost:8402")
    
    try:
        # Run client tests
        await run_client("http://localhost:8402")
        
    finally:
        # Cleanup
        await runner.cleanup()
        print("\nSERVER: Shut down")


if __name__ == "__main__":
    asyncio.run(main())
