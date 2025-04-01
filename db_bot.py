import logging
import asyncpg
import random
import string
import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from asyncpg import create_pool
from flask import Flask
import threading

# Bot credentials
API_TOKEN = "7431196503:AAEuMgD4NQMn96VJNL70snlb_vvWBso5idE"
GROUP_INVITE_LINK = "https://t.me/LorettaCryptoHub"
WHATSAPP_GROUP_LINK = "https://www.whatsapp.com/channel/0029Vb4A3wBJ93waVodoVb3o"
YOUR_TELEGRAM_USERNAME = "LorettaGifts"
BOT_USERNAME = "Loretta_Referrals_bot"
ADMIN_CHAT_IDS = {6315241288, 6375943693}  # Admin chat IDs

# Supabase Database Connection
DATABASE_URL = "postgresql://postgres:DEpTKHAnHspuSbnNgMxwCEuoXEtbBgTc@tramway.proxy.rlwy.net:55831/railway"

# Initialize bot and dispatcher
session = AiohttpSession()
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# Retry parameters for DB connection
MAX_RETRIES = 5  # Maximum retry attempts
RETRY_DELAY = 5  # Delay in seconds before retrying
DB_POOL = None

# Create a connection pool to PostgreSQL
async def create_db_pool():
    global DB_POOL
    try:
        DB_POOL = await create_pool(DATABASE_URL)
        print("✅ Connected to PostgreSQL with pooling!")
    except Exception as e:
        logging.error(f"❌ Error creating DB pool: {e}")

# Get a connection from the pool
async def get_db_connection():
    if not DB_POOL:
        await create_db_pool()
    try:
        return await DB_POOL.acquire()
    except Exception as e:
        logging.error(f"❌ Error acquiring DB connection: {e}")
        return None

# Generate a Referral Code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Escape MarkdownV2 Special Characters
def escape_markdown(text):
    special_chars = "_`*[]()~>#+-=|{}.!"
    return ''.join(f'\\{char}' if char in special_chars else char for char in text)

# Register User
async def register_user(telegram_id, username):
    db = await get_db_connection()
    if not db:
        return None

    # Check if the user already exists
    result = await db.fetchrow("SELECT referral_code FROM users WHERE telegram_id = $1", telegram_id)
    if result:
        await DB_POOL.release(db)
        return result["referral_code"]  # Return existing referral code

    # If user does not exist, create a new record
    referral_code = generate_referral_code()
    await db.execute(
        "INSERT INTO users (telegram_id, username, referral_code, referrals) VALUES ($1, $2, $3, $4)",
        telegram_id, username, referral_code, 0
    )
    await DB_POOL.release(db)
    return referral_code

# Handle /start Command
@dp.message(Command("start"))
async def handle_start(message: Message):
    db = await get_db_connection()
    if not db:
        await message.answer("❌ Database error! Please try again later.")
        return

    parts = message.text.split()
    telegram_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    referral_code = await register_user(telegram_id, username)

    if len(parts) > 1:
        referrer_code = parts[1]
        referrer = await db.fetchrow("SELECT telegram_id FROM users WHERE referral_code = $1", referrer_code)
        if referrer and referrer["telegram_id"] != telegram_id:
            await db.execute("UPDATE users SET referrals = referrals + 1 WHERE telegram_id = $1", referrer["telegram_id"])
            await message.answer("✅ You joined using a referral link!")

    await DB_POOL.release(db)

    buttons = [
        [InlineKeyboardButton(text="Refer a Friend ✅", callback_data="referral")],
        [InlineKeyboardButton(text="Join Loretta Crypto Hub ✅", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Join Our Whatsapp Group ✅", url=WHATSAPP_GROUP_LINK)]
    ]

    if telegram_id in ADMIN_CHAT_IDS:
        buttons.append([InlineKeyboardButton(text="View Leaderboard 🏆", callback_data="leaderboard")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer("📢 Welcome! Use the buttons below:", reply_markup=keyboard)

# Handle Referral Button Click
@dp.callback_query(F.data == "referral")
async def send_referral(event: CallbackQuery):
    telegram_id = event.from_user.id
    username = event.from_user.username or "Unknown"
    referral_code = await register_user(telegram_id, username)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"

    buttons = InlineKeyboardMarkup(inline_keyboard=[ 
        [InlineKeyboardButton(text="Refer a Friend ✅", callback_data="referral")],
        [InlineKeyboardButton(text="Join Loretta Crypto Hub ✅", url=GROUP_INVITE_LINK)],
        [InlineKeyboardButton(text="Join Our Whatsapp Group ✅", url=WHATSAPP_GROUP_LINK)]
    ])

    text = (f"🔗 Here is your referral link: {referral_link}\n"
            f"🎉 Invite friends and earn rewards!\n\n"
            f"📢 Join our group: {GROUP_INVITE_LINK}")

    await event.answer()
    await event.message.edit_text(text, reply_markup=buttons)

# Handle /leaderboard Command
@dp.callback_query(F.data == "leaderboard")
async def handle_leaderboard(event: CallbackQuery):
    if event.from_user.id not in ADMIN_CHAT_IDS:
        await event.answer("❌ You are not authorized to view the leaderboard.", show_alert=True)
        return

    db = await get_db_connection()
    if not db:
        await event.answer("❌ Database error! Please try again later.", show_alert=True)
        return

    top_users = await db.fetch("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    await DB_POOL.release(db)

    leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n" if top_users else "🏆 No referrals yet!"
    for i, row in enumerate(top_users, start=1):
        username = escape_markdown(row['username'])
        leaderboard_text += f"{i}\. {username}: {row['referrals']} referrals\n"

    await event.message.answer(leaderboard_text, parse_mode="MarkdownV2")

# Start the bot
async def main():
    print("🤖 Bot is running...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Flask for health check
    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is running!"

    @app.route('/health')
    def health_check():
        return "Bot is healthy and running!", 200

    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask, daemon=True).start()

    # Start bot
    asyncio.run(main())
