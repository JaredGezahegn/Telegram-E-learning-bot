from setuptools import setup, find_packages

setup(
    name="telegram-english-bot",
    version="1.0.0",
    description="Automated Telegram bot for daily English lessons",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "python-telegram-bot==20.7",
        "APScheduler==3.10.4",
        "hypothesis==6.92.1",
        "python-dotenv==1.0.0",
    ],
)