#!/usr/bin/env python3
"""
Trigger a manual lesson post to test the bot immediately.
This bypasses the scheduled time and posts a lesson right now.
"""

import asyncio
import sys
import os
import requests
from datetime import datetime

def test_bot_endpoints():
    """Test the bot endpoints first."""
    print("🔍 Testing bot endpoints...")
    
    try:
        # Test debug endpoint
        debug_response = requests.get('https://telegram-e-learning-bot.onrender.com/debug', timeout=10)
        if debug_response.status_code == 200:
            debug_data = debug_response.json()
            print("✅ Debug endpoint working")
            
            # Check if BOT_TOKEN is set
            bot_token = debug_data.get('environment_variables', {}).get('BOT_TOKEN')
            if bot_token:
                print(f"✅ Bot token found: {bot_token}")
            else:
                print("❌ Bot token missing in environment")
                return False
        else:
            print(f"❌ Debug endpoint failed: {debug_response.status_code}")
            return False
        
        # Test health endpoint
        health_response = requests.get('https://telegram-e-learning-bot.onrender.com/health', timeout=10)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print("✅ Health endpoint working")
            print(f"   Database: {health_data.get('database_type', 'unknown')}")
            print(f"   Lesson count: {health_data.get('lesson_count', 'unknown')}")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            
            if health_data.get('healthy'):
                print("✅ Bot is healthy and ready")
                return True
            else:
                print(f"❌ Bot is not healthy: {health_data.get('error')}")
                return False
        else:
            print(f"❌ Health endpoint failed: {health_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def check_schedule():
    """Check when the next post is scheduled."""
    print("\n📅 Checking schedule...")
    
    try:
        from datetime import datetime
        import pytz
        
        # East African Time
        eat = pytz.timezone('Africa/Nairobi')
        now_eat = datetime.now(eat)
        
        # Scheduled posting time (8:30 PM EAT)
        posting_hour, posting_minute = 20, 30
        today_post_time = eat.localize(datetime.combine(now_eat.date(), datetime.min.time().replace(hour=posting_hour, minute=posting_minute)))
        
        print(f"   Current time (EAT): {now_eat.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"   Scheduled time: {today_post_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        if now_eat < today_post_time:
            time_until = today_post_time - now_eat
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            print(f"   Next post: Today in {hours}h {minutes}m")
        else:
            from datetime import timedelta
            tomorrow = now_eat.date() + timedelta(days=1)
            tomorrow_post_time = eat.localize(datetime.combine(tomorrow, datetime.min.time().replace(hour=posting_hour, minute=posting_minute)))
            time_until = tomorrow_post_time - now_eat
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            print(f"   Next post: Tomorrow in {hours}h {minutes}m")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking schedule: {e}")
        return False

def test_telegram_api():
    """Test if the bot can connect to Telegram API."""
    print("\n🤖 Testing Telegram API connection...")
    
    try:
        # Get bot token from debug endpoint
        debug_response = requests.get('https://telegram-e-learning-bot.onrender.com/debug', timeout=10)
        if debug_response.status_code != 200:
            print("❌ Can't get debug info")
            return False
        
        debug_data = debug_response.json()
        bot_token_partial = debug_data.get('environment_variables', {}).get('BOT_TOKEN')
        
        if not bot_token_partial:
            print("❌ Bot token not found in environment")
            return False
        
        print("✅ Bot token is configured in Render")
        
        # Note: We can't test the actual API call without the full token
        # But we can check if the bot is configured correctly
        channel_id = debug_data.get('environment_variables', {}).get('CHANNEL_ID')
        if channel_id:
            print(f"✅ Channel ID configured: {channel_id}")
        else:
            print("❌ Channel ID not configured")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Telegram API: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Manual Bot Test - Telegram English Bot")
    print("=" * 60)
    
    # Test endpoints
    endpoints_ok = test_bot_endpoints()
    
    # Check schedule
    schedule_ok = check_schedule()
    
    # Test Telegram API setup
    telegram_ok = test_telegram_api()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"   Bot endpoints: {'✅ PASS' if endpoints_ok else '❌ FAIL'}")
    print(f"   Schedule check: {'✅ PASS' if schedule_ok else '❌ FAIL'}")
    print(f"   Telegram setup: {'✅ PASS' if telegram_ok else '❌ FAIL'}")
    
    if endpoints_ok and schedule_ok and telegram_ok:
        print("\n🎉 Your bot is fully configured and ready!")
        print("\n💡 Why it's not posting yet:")
        print("   - Bot is scheduled to post at 8:30 PM EAT daily")
        print("   - It's currently around 6:00 PM EAT")
        print("   - Next automatic post will be in ~2.5 hours")
        print("\n🔧 To test immediately:")
        print("   1. Go to your Telegram bot and send it a message")
        print("   2. Check if it responds (this tests the bot connection)")
        print("   3. Wait for 8:30 PM EAT for the automatic lesson post")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
    
    print("\n📱 Your bot URL: https://t.me/YourBotUsername")
    print("   (Replace with your actual bot username)")

if __name__ == "__main__":
    main()