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
BOT_USERNAME = "Loretta_Referrals_bot"

# ✅ Allowed Admins for /leaderboard
ADMIN_IDS = {6315241288, 6375943693}  # Allowed Telegram IDs

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


# ✅ Handle /leaderboard Command
@dp.message(Command("leaderboard"))
async def handle_leaderboard(message: Message):
    telegram_id = message.from_user.id

    # Check if the user is authorized
    if telegram_id not in ADMIN_IDS:
        await message.answer("❌ You are not authorized to view the leaderboard.")
        return

    db = await connect_db()
    if not db:
        await message.answer("❌ Database error! Please try again later.")
        return

    try:
        top_users = await db.fetch("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
        
        if not top_users:
            leaderboard_text = "🏆 No referrals yet!"
        else:
            leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n"
            for i, row in enumerate(top_users, start=1):
                leaderboard_text += f"{i}. {row['username']}: {row['referrals']} referrals\n"

        print("✅ Sending leaderboard...")
        await message.answer(leaderboard_text, parse_mode="Markdown")
    except Exception as e:
        print(f"❌ Error fetching leaderboard: {e}")
        await message.answer("❌ Failed to fetch leaderboard.")
    finally:
        await db.close()

# ✅ Start the bot
async def main():
    print("🤖 Bot is running...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
