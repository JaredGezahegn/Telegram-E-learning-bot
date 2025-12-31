# 🤖 Telegram English Learning Bot

An intelligent Telegram bot that delivers daily English lessons with interactive quizzes to help users improve their English skills.

## ✨ Features

- 📚 **Daily Lesson Delivery** - Automatically posts English lessons at scheduled times
- 🧠 **Interactive Quizzes** - Generates 4-5 option quizzes based on lesson content
- 🎯 **Smart Content** - Grammar, vocabulary, and common mistakes lessons
- 🔄 **Dual Database Support** - SQLite for development, Supabase for production
- 📊 **Usage Tracking** - Monitors lesson usage and posting history
- 🛡️ **Error Resilience** - Built-in retry logic and graceful error handling
- ⚙️ **Easy Deployment** - Ready for Railway, Render, Heroku, and other platforms

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/JaredGezahegn/Telegram-E-learning-bot.git
cd Telegram-E-learning-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your bot token and channel ID
```

### 4. Load Sample Lessons
```bash
python -m src.load_lessons
```

### 5. Run Bot
```bash
python -m src.main
```

## 📋 Configuration

### Required Environment Variables
- `BOT_TOKEN` - Your Telegram bot token from @BotFather
- `CHANNEL_ID` - Target channel/chat ID (e.g., @mychannel or -1001234567890)

### Optional Configuration
- `POSTING_TIME` - Daily posting time (default: 09:00)
- `TIMEZONE` - Timezone for scheduling (default: UTC)
- `ENABLE_QUIZZES` - Enable quiz generation (default: true)
- `QUIZ_DELAY_MINUTES` - Minutes between lesson and quiz (default: 5)

## 🗄️ Database Options

### Development (SQLite)
```env
DATABASE_TYPE=sqlite
DATABASE_PATH=lessons.db
```

### Production (Supabase)
```env
DATABASE_TYPE=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
```

## 🌐 Production Deployment

### Railway Deployment
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically

### Supabase Setup
1. Create Supabase project
2. Run SQL commands from `SUPABASE_SETUP.md`
3. Load lessons using `setup_supabase.py`
4. Update environment variables

See `QUICK_DEPLOY.md` for detailed deployment instructions.

## 📚 Lesson Content

The bot includes 51+ English lessons covering:
- **Grammar** (20 lessons) - Tenses, conditionals, articles, etc.
- **Vocabulary** (18 lessons) - Business, emotions, academic terms, etc.
- **Common Mistakes** (13 lessons) - Frequent errors and corrections

Lessons are stored in `data/seed_lessons.json` and can be customized.

## 🧠 Quiz Generation

The bot automatically generates interactive quizzes with:
- 4-5 multiple choice options
- Context-aware distractors
- Explanations for correct answers
- Category-specific question types

## 🛠️ Development

### Project Structure
```
src/
├── models/          # Data models (Lesson, Quiz, etc.)
├── services/        # Business logic and external APIs
├── main.py         # Application entry point
└── config.py       # Configuration management

data/
├── seed_lessons.json    # Sample lesson content
└── load_seed_data.py   # Data loading utilities

scripts/            # Deployment scripts
tests/             # Test files
```

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Lessons
1. Edit `data/seed_lessons.json`
2. Run `python -m src.load_lessons` to reload
3. Or add via Supabase dashboard in production

## 📊 Monitoring

The bot includes comprehensive monitoring:
- Health check endpoint (port 8000)
- Structured logging
- Error tracking and recovery
- Resource monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- Check `DEPLOYMENT.md` for deployment issues
- Review `SUPABASE_SETUP.md` for database setup
- Open an issue for bugs or feature requests

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Advanced quiz types
- [ ] Progress tracking per user
- [ ] Lesson difficulty adaptation
- [ ] Voice message support

---

Made with ❤️ for English learners worldwide