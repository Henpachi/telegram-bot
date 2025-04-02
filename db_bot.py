import logging
import random
import string
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
import threading

# Bot credentials
API_TOKEN = "7431196503:AAEuMgD4NQMn96VJNL70snlb_vvWBso5idE"
GROUP_INVITE_LINK = "https://t.me/LorettaCryptoHub"
WHATSAPP_GROUP_LINK = "https://www.whatsapp.com/channel/0029Vb4A3wBJ93waVodoVb3o"
YOUR_TELEGRAM_USERNAME = "LorettaGifts"
BOT_USERNAME = "Loretta_Referrals_bot"
ADMIN_CHAT_IDS = {6315241288, 6375943693}  # Admin chat IDs

# MongoDB Database Connection
MONGO_URI = os.getenv("MONGO_URI")  # Fetch Mongo URI from environment variable
DATABASE_NAME = "referralbot"  # The database name is referralbot
USERS_COLLECTION = "users"  # Collection name is users

# Initialize bot and dispatcher
session = AiohttpSession()
bot = Bot(token=API_TOKEN, session=session)
dp = Dispatcher()

# MongoDB Client
client = None
db = None

# Retry parameters for DB connection
MAX_RETRIES = 5  # Maximum retry attempts
RETRY_DELAY = 5  # Delay in seconds before retrying

# Create MongoDB client
async def create_db_client():
    global client, db
    retries = 0
    while retries < MAX_RETRIES:
        try:
            client = AsyncIOMotorClient(MONGO_URI)
            db = client[DATABASE_NAME]
            logging.info("✅ Connected to MongoDB!")
            return
        except Exception as e:
            retries += 1
            logging.error(f"❌ Error connecting to MongoDB: {e}. Retrying {retries}/{MAX_RETRIES}...")
            await asyncio.sleep(RETRY_DELAY)
    logging.critical("❌ Failed to connect to MongoDB after multiple retries.")

# Generate a Referral Code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Escape MarkdownV2 Special Characters
def escape_markdown(text):
    special_chars = "_`*[]()~>#+-=|{}.!"
    return ''.join(f'\\{char}' if char in special_chars else char for char in text)

# Register User
async def register_user(telegram_id, username):
    # Access the MongoDB collection in the correct database
    collection = db[USERS_COLLECTION]
    
    # Check if the user already exists
    user = await collection.find_one({"telegram_id": telegram_id})
    if user:
        return user["referral_code"]  # Return existing referral code

    # If user does not exist, create a new record
    referral_code = generate_referral_code()
    new_user = {
        "telegram_id": telegram_id,
        "username": username,
        "referral_code": referral_code,
        "referrals": 0
    }
    await collection.insert_one(new_user)
    return referral_code

# Handle /start Command
@dp.message(Command("start"))
async def handle_start(message: Message):
    await create_db_client()  # Ensure the DB connection is established
    
    parts = message.text.split()
    telegram_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    referral_code = await register_user(telegram_id, username)

    if len(parts) > 1:
        referrer_code = parts[1]
        referrer = await db[USERS_COLLECTION].find_one({"referral_code": referrer_code})
        if referrer and referrer["telegram_id"] != telegram_id:
            await db[USERS_COLLECTION].update_one(
                {"telegram_id": referrer["telegram_id"]},
                {"$inc": {"referrals": 1}}
            )
            await message.answer("✅ You joined using a referral link!")

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

    # Fetch top users from the correct collection in the referralbot database
    top_users = await db[USERS_COLLECTION].find().sort("referrals", -1).limit(10).to_list(length=10)

    leaderboard_text = "🏆 *Referral Leaderboard* 🏆\n\n" if top_users else "🏆 No referrals yet!"
    for i, user in enumerate(top_users, start=1):
        username = escape_markdown(user['username'])
        leaderboard_text += f"{i}. {username}: {user['referrals']} referrals\n"

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
