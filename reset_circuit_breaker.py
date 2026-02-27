#!/usr/bin/env python3
"""
Reset the Telegram API circuit breaker manually.
Use this when you've fixed the underlying issue and want to resume operations immediately.
"""

import asyncio
import sys
from src.services.resilience_service import get_resilience_service
from src.services.logging_service import get_logging_service

async def reset_circuit_breaker():
    """Reset the Telegram API circuit breaker."""
    try:
        # Initialize services
        logging_service = get_logging_service()
        resilience_service = get_resilience_service()
        
        # Start resilience service
        await resilience_service.start()
        
        # Check current state
        current_state = resilience_service.get_circuit_breaker_state("telegram_api")
        print(f"Current circuit breaker state: {current_state}")
        
        if current_state == "open":
            # Manually reset the circuit breaker
            if "telegram_api" in resilience_service.circuit_breakers:
                resilience_service.circuit_breakers["telegram_api"]["state"] = "closed"
                resilience_service.circuit_breakers["telegram_api"]["failure_count"] = 0
                resilience_service.circuit_breakers["telegram_api"]["last_failure"] = None
                
                print("✅ Circuit breaker has been reset to 'closed' state")
                print("The bot can now attempt to send messages again")
            else:
                print("⚠️ Circuit breaker not found in registry")
        elif current_state == "half_open":
            print("Circuit breaker is in 'half_open' state - it will close on next successful operation")
        else:
            print("Circuit breaker is already closed - no action needed")
        
        # Show full status
        status = resilience_service.get_resilience_status()
        if "circuit_breakers" in status:
            print("\nAll circuit breakers:")
            for name, breaker in status["circuit_breakers"].items():
                print(f"  {name}: {breaker['state']} (failures: {breaker['failure_count']})")
        
        await resilience_service.stop()
        
    except Exception as e:
        print(f"❌ Error resetting circuit breaker: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Resetting Telegram API circuit breaker...")
    asyncio.run(reset_circuit_breaker())
