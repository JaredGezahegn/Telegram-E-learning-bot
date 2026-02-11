# Telegram English Bot - Startup Guide

## Problem Identified

The bot was **not running** - that's why no lessons have been posted in weeks. The bot needs to be running continuously for the scheduler to work.

## Solution

### Quick Start (Windows)

1. **Double-click `start_bot.bat`** - This will start the bot and keep it running

OR

2. **Open Command Prompt and run:**
   ```cmd
   python src/main.py
   ```

The bot will:
- Start immediately
- Post lessons daily at 21:00 (9 PM) Africa/Nairobi time
- Keep running until you stop it (Ctrl+C)

### Verify Bot is Running

After starting, you should see:
```
Scheduler running: True
Next run time: 2026-02-12T21:00:00+03:00
Posting time: 21:00 Africa/Nairobi
Bot polling started for interactive features
Telegram English Bot started successfully!
Daily lessons will be posted automatically
```

### Important Notes

1. **The bot must stay running** - If you close the terminal/command prompt, the bot stops
2. **Next lesson post**: Tomorrow at 21:00 Africa/Nairobi time (check the "Next run time" in the output)
3. **To stop the bot**: Press Ctrl+C in the terminal

### For Production/Server Deployment

If you want the bot to run permanently (even after restarting your computer), you need to:

1. **Deploy to a cloud service** (Render, Railway, Heroku, etc.)
2. **Or use Windows Task Scheduler** to start the bot on system startup
3. **Or use a process manager** like PM2 or NSSM

### Testing the Bot

To test if the bot can post immediately (without waiting for 21:00):

```cmd
python send_lesson_now.py
```

This will post a lesson right away to verify everything works.

### Troubleshooting

**Bot exits immediately:**
- Check `bot.log` for errors
- Verify your `.env` file has correct credentials
- Run `python diagnose_bot_issue.py` to check configuration

**No lessons posted:**
- Make sure the bot is actually running (check Task Manager for python.exe)
- Check the "Next run time" matches your expected posting time
- Verify timezone is correct in `.env` (TIMEZONE=Africa/Nairobi)

**Unicode errors in console:**
- These are harmless display issues on Windows
- The bot still works correctly
- Check `bot.log` file for clean output

### Current Configuration

- **Posting Time**: 21:00 (9 PM)
- **Timezone**: Africa/Nairobi (EAT - East Africa Time)
- **Database**: Supabase
- **Quizzes**: Enabled (5 minutes after lesson)

### Next Steps

1. Start the bot using `start_bot.bat`
2. Leave it running
3. Wait for 21:00 Africa/Nairobi time
4. Check your Telegram channel for the lesson post
5. For permanent deployment, consider using a cloud service

## Why Lessons Weren't Posted

The bot was starting but immediately exiting because:
1. No process was keeping it running
2. The scheduler needs the bot process to stay alive
3. Without a running process, scheduled tasks never execute

Now that you know to keep the bot running, lessons will post automatically every day at 21:00.
