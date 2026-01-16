# Python Version Downgrade Instructions

## Problem
Your current Python version (3.14.0) is too new and causes compatibility issues with the `httpcore` library used by `python-telegram-bot`.

## Solution
Downgrade to Python 3.11.x (recommended: 3.11.9)

---

## Windows Instructions

### Option 1: Using Python Installer (Recommended)

1. **Download Python 3.11.9:**
   - Visit: https://www.python.org/downloads/release/python-3119/
   - Download: "Windows installer (64-bit)"

2. **Install Python 3.11.9:**
   - Run the installer
   - ✅ Check "Add Python 3.11 to PATH"
   - Click "Install Now"

3. **Verify Installation:**
   ```cmd
   python --version
   ```
   Should show: `Python 3.11.9`

4. **Recreate Virtual Environment:**
   ```cmd
   # Remove old virtual environment
   rmdir /s /q venv
   
   # Create new virtual environment with Python 3.11
   python -m venv venv
   
   # Activate virtual environment
   venv\Scripts\activate
   
   # Upgrade pip
   python -m pip install --upgrade pip
   
   # Install dependencies
   pip install -r requirements.txt
   ```

5. **Verify Installation:**
   ```cmd
   python -c "import telegram; print('Telegram bot library OK')"
   ```

### Option 2: Using pyenv-win

1. **Install pyenv-win:**
   ```powershell
   Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
   ```

2. **Install Python 3.11.9:**
   ```cmd
   pyenv install 3.11.9
   pyenv global 3.11.9
   ```

3. **Follow steps 3-5 from Option 1**

---

## Linux/Mac Instructions

### Using pyenv (Recommended)

1. **Install pyenv (if not installed):**
   
   **Linux:**
   ```bash
   curl https://pyenv.run | bash
   ```
   
   **Mac:**
   ```bash
   brew install pyenv
   ```

2. **Install Python 3.11.9:**
   ```bash
   pyenv install 3.11.9
   pyenv global 3.11.9
   ```

3. **Recreate Virtual Environment:**
   ```bash
   # Remove old virtual environment
   rm -rf venv
   
   # Create new virtual environment
   python -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate
   
   # Upgrade pip
   python -m pip install --upgrade pip
   
   # Install dependencies
   pip install -r requirements.txt
   ```

4. **Verify Installation:**
   ```bash
   python --version
   python -c "import telegram; print('Telegram bot library OK')"
   ```

---

## After Downgrade

### Run Tests to Verify Everything Works

```bash
# Run all tests
python -m pytest tests/ -v

# Or run specific test suites
python -m pytest tests/test_bot_controller.py -v
python -m pytest tests/test_scheduler.py -v
```

### Expected Results
- ✅ All 75+ tests should pass
- ✅ No import errors
- ✅ Bot should start successfully

### Start the Bot

```bash
python src/main.py
```

You should see:
```
Starting Telegram English Bot (Simple Version)
Configuration validated - Database: supabase
Health service started on port 8000
Lesson manager initialized
Bot controller created successfully
Scheduler service started successfully
🎉 Telegram English Bot started successfully!
📅 Daily lessons will be posted automatically
```

---

## Update Deployment Configuration

### Update runtime.txt (for Render/Heroku)

Create or update `runtime.txt`:
```
python-3.11.9
```

### Update .github/workflows/ci.yml

Update the Python version in your CI/CD:
```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.11'
```

### Update Docker (if using)

Update your Dockerfile:
```dockerfile
FROM python:3.11.9-slim
```

---

## Troubleshooting

### Issue: "python: command not found" after installation

**Solution:** Restart your terminal or add Python to PATH manually.

### Issue: Multiple Python versions conflict

**Solution:** Use full path to Python 3.11:
```bash
# Windows
C:\Python311\python.exe -m venv venv

# Linux/Mac
/usr/local/bin/python3.11 -m venv venv
```

### Issue: pip install fails

**Solution:** Upgrade pip first:
```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Issue: Tests still fail after downgrade

**Solution:** 
1. Ensure virtual environment is activated
2. Verify Python version: `python --version`
3. Reinstall dependencies: `pip install --force-reinstall -r requirements.txt`
4. Clear pytest cache: `rm -rf .pytest_cache`

---

## Why Python 3.11 and not 3.12 or 3.13?

- **Python 3.11:** Most stable, best compatibility with all dependencies
- **Python 3.12:** Works but has deprecation warnings (datetime.utcnow, sqlite3)
- **Python 3.13:** May have compatibility issues with some packages
- **Python 3.14:** Too new, breaks httpcore/telegram libraries

**Recommendation:** Use Python 3.11.9 for production stability.

---

## Quick Reference

```bash
# Check current Python version
python --version

# Remove old venv
rm -rf venv  # Linux/Mac
rmdir /s /q venv  # Windows

# Create new venv with Python 3.11
python3.11 -m venv venv  # Linux/Mac
python -m venv venv  # Windows (after installing 3.11)

# Activate venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start bot
python src/main.py
```

---

## Need Help?

If you encounter issues:
1. Check Python version: `python --version`
2. Check pip version: `pip --version`
3. Check installed packages: `pip list`
4. Run diagnostics: `python -c "import sys; print(sys.version); import telegram; print('OK')"`

---

**Last Updated:** January 15, 2026  
**Recommended Python Version:** 3.11.9
