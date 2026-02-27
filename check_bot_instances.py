#!/usr/bin/env python3
"""
Check for multiple bot instances and help resolve conflicts.
"""

import asyncio
from telegram import Bot
from telegram.error import Conflict, TelegramError
from src.config import Config

async def check_instances():
    """Check for conflicting bot instances."""
    try:
        config = Config()
        bot = Bot(token=config.telegram_bot_token)
        
        print("🔍 Checking for bot instance conflicts...\n")
        
        # Try to get bot info
        me = await bot.get_me()
        print(f"✅ Bot: @{me.username}")
        print(f"   ID: {me.id}")
        print()
        
        # Try to get updates (this will fail if another instance is running)
        print("Testing for conflicts...")
        try:
            # Use a very short timeout to test quickly
            updates = await bot.get_updates(timeout=1, limit=1)
            print("✅ No conflicts detected - this bot can receive updates")
            print(f"   Pending updates: {len(updates)}")
            
        except Conflict as e:
            print("❌ CONFLICT DETECTED!")
            print(f"   Error: {e}")
            print()
            print("📋 This means another bot instance is running.")
            print()
            print("Common causes:")
            print("   1. Bot is running on Render AND locally")
            print("   2. Multiple Render instances are active")
            print("   3. Previous instance didn't shut down properly")
            print()
            print("Solutions:")
            print("   1. Stop all local bot instances")
            print("   2. On Render: Go to Dashboard → Manual Deploy → Clear build cache & deploy")
            print("   3. Or use webhook mode instead of polling (recommended for production)")
            print()
            print("To use webhook mode:")
            print("   - Set TELEGRAM_USE_WEBHOOK=true in environment")
            print("   - Set WEBHOOK_URL to your Render URL")
            print("   - Webhooks don't have this conflict issue")
            
        except TelegramError as e:
            print(f"⚠️ Telegram API error: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_instances())
