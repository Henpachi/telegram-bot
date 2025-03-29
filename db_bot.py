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
API_TOKEN = "YOUR_BOT_API_TOKEN"
GROUP_INVITE_LINK = "https://t.me/LorettaCryptoHub"
WHATSAPP_CHANNEL_LINK = "https://www.whatsapp.com/channel/0029Vb4A3wBJ93waVodoVb3o"
AUTHORIZED_USERS = {6315241288, 6375943693}  # List of users allowed to check leaderboard
BOT_USERNAME = "Loretta_Referrals_bot"

# ✅ Database Connection
DATABASE_URL = "YOUR_DATABASE_URL"

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

# ✅ Handle /leaderboard Command
@dp.message(Command("leaderboard"))
async def handle_leaderboard(message: Message):
    if message.from_user.id not in AUTHORIZED_USERS:
        await message.answer("❌ You are not authorized to view the leaderboard.")
        return

    db = await connect_db()
    if not db:
        await message.answer("❌ Database error! Please try again later.")
        return

    try:
        top_users = await db.fetch("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
        leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n" if top_users else "🏆 No referrals yet!"

        for i, row in enumerate(top_users, start=1):
            leaderboard_text += f"{i}. {row['username']}: {row['referrals']} referrals\n"

        await message.answer(leaderboard_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error fetching leaderboard: {e}")
        await message.answer("❌ Failed to fetch leaderboard data.")
    finally:
        await db.close()

# ✅ Start the bot
async def main():
    print("🤖 Bot is running...")
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
