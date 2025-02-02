import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
SOLANA_ADDRESS = os.getenv("SOLANA_WALLET_ADDRESS")
DATABASE_NAME = "orders.db"

PACKAGES = [
    {
        "key": "basic",
        "title": "🥈 BASIC LAUNCH",
        "price": "0.1 SOL",
        "features": ["Custom Design", "24h Delivery"],
        "callback_data": "basic_package",
    },
    {
         "key": "pro",
        "title": "🥇 PRO LAUNCH",
        "price": "2 SOL",
        "features": ["Everything in Basic", "Staking Interface", "Priority Support"],
        "callback_data": "pro_package",
    },
    {
        "key": "custom",
        "title": "👑 Custom MOON LAUNCH",
        "price": "4 SOL",
        "features": ["Tailored Web3 Features", "Custom Smart Contracts", "Flexible Pricing"],
        "callback_data": "custom_package",
    },
]

WELCOME_MESSAGE = """🚀 *Welcome to MoonLaunch Website Builder!*  

We craft high-converting crypto websites that take your memecoin to the moon!  
Our proven designs have helped launch countless successful tokens.  

*Ready to give your coin the website it deserves?*  

🎯 *Select Your Launch Package:*  
"""
