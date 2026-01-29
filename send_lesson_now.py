#!/usr/bin/env python3
"""Send a lesson immediately to test the bot."""

import asyncio
import os
import json
from telegram import Bot

# Bot configuration - Load from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("CHANNEL_ID")

if not BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN or BOT_TOKEN environment variable not set")
    exit(1)

if not CHANNEL_ID:
    print("❌ Error: TELEGRAM_CHANNEL_ID or CHANNEL_ID environment variable not set")
    exit(1)

async def send_lesson():
    """Send a lesson to the channel."""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        # Test bot info
        me = await bot.get_me()
        print(f"Bot info: {me.first_name} (@{me.username})")
        
        # Load a lesson from the data
        lesson_data = None
        try:
            with open('data/seed_lessons.json', 'r') as f:
                lessons = json.load(f)
                if lessons:
                    lesson_data = lessons[0]  # Get first lesson
        except Exception as e:
            print(f"Could not load lesson data: {e}")
        
        if not lesson_data:
            # Use a simple test lesson
            lesson_data = {
                "title": "Test Lesson - Present Simple Tense",
                "content": "The present simple tense is used for habits, facts, and general truths.\n\nExamples:\n• I work every day.\n• She likes coffee.\n• The sun rises in the east.",
                "level": "beginner",
                "category": "grammar"
            }
        
        # Format the lesson message
        message_text = f"""📚 **Daily English Lesson**

🎯 **{lesson_data['title']}**

{lesson_data['content']}

📊 **Level:** {lesson_data.get('level', 'N/A').title()}
📂 **Category:** {lesson_data.get('category', 'N/A').title()}

---
🤖 *Automated daily lesson at 8:30 PM EAT*
💡 *Keep learning English every day!*"""
        
        # Send the lesson
        message = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message_text,
            parse_mode="Markdown"
        )
        
        print(f"✅ Lesson sent successfully!")
        print(f"   Message ID: {message.message_id}")
        print(f"   Lesson: {lesson_data['title']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending lesson: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    print("📚 Sending English Lesson Now...")
    print("=" * 50)
    
    success = await send_lesson()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Lesson sent successfully! Check your Telegram channel.")
        print("🔧 This confirms your bot is working correctly.")
        print("⏰ The scheduler should now post automatically at 8:30 PM EAT daily.")
    else:
        print("❌ Failed to send lesson. Check the error messages above.")

if __name__ == "__main__":
    asyncio.run(main())