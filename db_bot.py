import logging
import asyncpg
import random
import string
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from flask import Flask
import threading

# ✅ Bot credentials (for educational use only)
API_TOKEN = "7431196503:AAEuMgD4NQMn96VJNL70snlb_vvWBso5idE"
GROUP_INVITE_LINK = "https://t.me/LorettaCryptoHub"
WHATSAPP_CHANNEL_LINK = "https://www.whatsapp.com/channel/0029Vb4A3wBJ93waVodoVb3o"
YOUR_TELEGRAM_USERNAME = "LorettaGifts"
BOT_USERNAME = "Loretta_Referrals_bot"

# ✅ Database Connection
DATABASE_URL = "postgresql://postgres:DEpTKHAnHspuSbnNgMxwCEuoXEtbBgTc@tramway.proxy.rlwy.net:55831/railway"

# ✅ Initialize bot and dispatcher
session = AiohttpSession()
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()


# ✅ Connect to PostgreSQL
async def connect_db():
    try:
        db = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to PostgreSQL!")
        return db
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None


# ✅ Generate Referral Code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


# ✅ Register User
async def register_user(telegram_id, username):
    db = await connect_db()
    if not db:
        return None

    try:
        result = await db.fetchrow("SELECT referral_code FROM users WHERE telegram_id = $1", telegram_id)
        if result:
            return result["referral_code"]

        referral_code = generate_referral_code()
        await db.execute("INSERT INTO users (telegram_id, username, referral_code, referrals) VALUES ($1, $2, $3, $4)",
                         telegram_id, username, referral_code, 0)

        return referral_code
    except Exception as e:
        print(f"❌ Error registering user: {e}")
        return None
    finally:
        await db.close()


# ✅ Scheduled Leaderboard Sender
async def send_leaderboard():
    db = await connect_db()
    if not db:
        return

    try:
        top_users = await db.fetch("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
        leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n" if top_users else "🏆 No referrals yet!"

        for i, row in enumerate(top_users, start=1):
            leaderboard_text += f"{i}. {row['username']}: {row['referrals']} referrals\n"

        ADMIN_CHAT_ID = 6315241288  # Replace with your chat ID
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=leaderboard_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error sending leaderboard: {e}")
    finally:
        await db.close()


async def leaderboard_scheduler():
    while True:
        await send_leaderboard()
        await asyncio.sleep(86400)  # 24 hours


# ✅ Start the bot
async def main():
    print("🤖 Bot is running...")
    asyncio.create_task(leaderboard_scheduler())
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


# ✅ Flask for uptime
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Start Flask in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
