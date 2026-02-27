#!/usr/bin/env python3
"""
Diagnose why Telegram API is failing.
This script tests the connection and identifies the root cause.
"""

import asyncio
import sys
from telegram import Bot
from telegram.error import TelegramError
from src.config import Config

async def diagnose_telegram():
    """Test Telegram connection and identify issues."""
    try:
        config = Config()
        
        print("🔍 Diagnosing Telegram API connection...")
        print(f"Bot Token: {config.telegram_bot_token[:10]}...{config.telegram_bot_token[-5:]}")
        print(f"Channel ID: {config.telegram_channel_id}")
        print()
        
        # Create bot instance
        bot = Bot(token=config.telegram_bot_token)
        
        # Test 1: Get bot info
        print("Test 1: Getting bot information...")
        try:
            me = await bot.get_me()
            print(f"✅ Bot connected: @{me.username} ({me.first_name})")
        except TelegramError as e:
            print(f"❌ Failed to get bot info: {e}")
            print("   This usually means the bot token is invalid")
            return
        
        # Test 2: Get chat info
        print("\nTest 2: Checking channel access...")
        try:
            chat = await bot.get_chat(chat_id=config.telegram_channel_id)
            print(f"✅ Channel found: {chat.title or chat.username or chat.id}")
            print(f"   Type: {chat.type}")
        except TelegramError as e:
            print(f"❌ Failed to access channel: {e}")
            print("   Possible issues:")
            print("   - Bot is not added to the channel")
            print("   - Bot doesn't have admin rights")
            print("   - Channel ID is incorrect")
            return
        
        # Test 3: Check bot permissions
        print("\nTest 3: Checking bot permissions...")
        try:
            member = await bot.get_chat_member(
                chat_id=config.telegram_channel_id,
                user_id=me.id
            )
            print(f"✅ Bot status in channel: {member.status}")
            
            if member.status in ["administrator", "creator"]:
                print("   Bot has admin rights")
                if hasattr(member, 'can_post_messages'):
                    if member.can_post_messages:
                        print("   ✅ Can post messages")
                    else:
                        print("   ❌ Cannot post messages - check admin permissions")
            elif member.status == "member":
                print("   ⚠️ Bot is only a member, not an admin")
                print("   For channels, the bot needs admin rights to post")
            else:
                print(f"   ⚠️ Unexpected status: {member.status}")
                
        except TelegramError as e:
            print(f"❌ Failed to check permissions: {e}")
        
        # Test 4: Try sending a test message
        print("\nTest 4: Attempting to send a test message...")
        try:
            message = await bot.send_message(
                chat_id=config.telegram_channel_id,
                text="🧪 Test message from diagnostic script\n\nIf you see this, the bot is working correctly!",
                disable_notification=True
            )
            print(f"✅ Test message sent successfully!")
            print(f"   Message ID: {message.message_id}")
            print("\n✅ All tests passed! The bot should be working now.")
            
        except TelegramError as e:
            print(f"❌ Failed to send test message: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("\n   Common causes:")
            print("   - Bot lacks 'Post Messages' permission")
            print("   - Channel privacy settings block the bot")
            print("   - Rate limiting (too many requests)")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(diagnose_telegram())
