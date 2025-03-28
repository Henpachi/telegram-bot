import logging
import asyncpg
import random
import string
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command

# Bot credentials
API_TOKEN = "7431196503:AAEuMgD4NQMn96VJNL70snlb_vvWBso5idE"
GROUP_INVITE_LINK = "https://t.me/LorettaCryptoHub"
YOUR_TELEGRAM_USERNAME = "LorettaGifts"
BOT_USERNAME = "Loretta_Referrals_bot"

# Supabase Database Connection
DATABASE_URL = "postgresql://postgres:DEpTKHAnHspuSbnNgMxwCEuoXEtbBgTc@tramway.proxy.rlwy.net:55831/railway"

# Initialize bot and dispatcher
session = AiohttpSession()
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# Connect to PostgreSQL
async def connect_db():
    try:
        db = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to PostgreSQL!")
        return db
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return None

# Generate a Referral Code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Register User
async def register_user(telegram_id, username):
    db = await connect_db()
    if not db:
        return None

    result = await db.fetchrow("SELECT referral_code FROM users WHERE telegram_id = $1", telegram_id)
    if result:
        await db.close()
        return result["referral_code"]

    referral_code = generate_referral_code()
    await db.execute("INSERT INTO users (telegram_id, username, referral_code, referrals) VALUES ($1, $2, $3, $4)", telegram_id, username, referral_code, 0)
    await db.close()
    return referral_code

# Handle /start Command
@dp.message(Command("start"))
async def handle_start(message: Message):
    db = await connect_db()
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

    await db.close()

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Refer a Friend ✅", callback_data="referral")],
        [InlineKeyboardButton(text="Join Loretta Crypto Hub ✅", url=GROUP_INVITE_LINK)]
    ])

    await message.answer("📢 Welcome! Use the buttons below:", reply_markup=buttons)

# Handle Referral Button Click
@dp.callback_query(F.data == "referral")
async def send_referral(event: CallbackQuery):
    telegram_id = event.from_user.id
    username = event.from_user.username or "Unknown"
    referral_code = await register_user(telegram_id, username)
    referral_link = f"https://t.me/{BOT_USERNAME}?start={referral_code}"

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Refer a Friend ✅", callback_data="referral")],
        [InlineKeyboardButton(text="Join Loretta Crypto Hub ✅", url=GROUP_INVITE_LINK)]
    ])

    text = (f"🔗 Here is your referral link: {referral_link}\n"
            f"🎉 Invite friends and earn rewards!\n\n"
            f"📢 Join our group: {GROUP_INVITE_LINK}")

    await event.answer()
    await event.message.edit_text(text, reply_markup=buttons)

# Start the bot
async def main():
    print("🤖 Bot is running...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from flask import Flask
    import threading

    app = Flask(__name__)

    @app.route('/')
    def home():
        return "Bot is running!"

    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
