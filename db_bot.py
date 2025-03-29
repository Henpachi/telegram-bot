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

# ✅ Bot credentials (DO NOT CHANGE API OR DATABASE URL)
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

ADMIN_CHAT_IDS = {6315241288, 6375943693}  # Added new admin chat ID

async def connect_db():
    try:
        return await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None


def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


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
    finally:
        await db.close()


@dp.message(Command("start"))
async def handle_start(message: Message):
    parts = message.text.split()
    telegram_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    referral_code = await register_user(telegram_id, username)
    if not referral_code:
        await message.answer("❌ Database error! Please try again later.")
        return

    db = await connect_db()
    if db and len(parts) > 1:
        referrer_code = parts[1]
        referrer = await db.fetchrow("SELECT telegram_id FROM users WHERE referral_code = $1", referrer_code)
        if referrer and referrer["telegram_id"] != telegram_id:
            await db.execute("UPDATE users SET referrals = referrals + 1 WHERE telegram_id = $1",
                             referrer["telegram_id"])
            await message.answer("✅ You joined using a referral link!")
        await db.close()

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Refer a Friend ✅", callback_data="referral")],
        [InlineKeyboardButton(text="Join Loretta Crypto Hub ✅", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Join Our WhatsApp Channel ✅", url=WHATSAPP_CHANNEL_LINK)]
    ])
    await message.answer("📢 Welcome! Use the buttons below:", reply_markup=buttons)


@dp.message(Command("leaderboard"))
async def handle_leaderboard(message: Message):
    if message.from_user.id not in ADMIN_CHAT_IDS:
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
    finally:
        await db.close()


async def send_leaderboard_message():
    db = await connect_db()
    if not db:
        return
    try:
        top_users = await db.fetch("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
        leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n" if top_users else "🏆 No referrals yet!"
        for i, row in enumerate(top_users, start=1):
            leaderboard_text += f"{i}. {row['username']}: {row['referrals']} referrals\n"
        for admin_id in ADMIN_CHAT_IDS:
            await bot.send_message(chat_id=admin_id, text=leaderboard_text, parse_mode="Markdown")
    finally:
        await db.close()


async def leaderboard_scheduler():
    while True:
        await send_leaderboard_message()
        await asyncio.sleep(86400)


async def main():
    print("🤖 Bot is running...")
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(leaderboard_scheduler())
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is running!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


threading.Thread(target=run_flask, daemon=True).start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
