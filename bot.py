import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from motor.motor_asyncio import AsyncIOMotorClient

# Railway Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
GROUP_ID = os.getenv("GROUP_ID")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# MongoDB Connection
client = AsyncIOMotorClient(MONGO_URL)
db = client.dating_bot
users_col = db.users

class ProfileSG(StatesGroup):
    name = State()
    gender = State()
    photo = State()

# --- Keyboards ---
def get_main_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔎 တခြားသူတွေရှာမယ်")],
        [KeyboardButton(text="👤 ကျွန်တော့် Profile")],
        [KeyboardButton(text="⚙️ Profile ပြင်မယ်")]
    ], resize_keyboard=True)

def get_gender_kb():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="ယောကျာ်း"), KeyboardButton(text="မိန်းမ")]
    ], resize_keyboard=True)

def get_like_kb(target_id):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=f"❤️ Like_{target_id}"), KeyboardButton(text="👎 Skip")]
    ], resize_keyboard=True)

# --- Handlers ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await message.answer("မြန်မာ ချစ်သူရှာမယ် Bot ကနေ ကြိုဆိုလိုက်ပါတယ် 💞။ Profile အရင်ဆောက်ရအောင်! သင့်နာမည် ဘယ်လိုခေါ်လဲ?", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ProfileSG.name)
    else:
        await message.answer(f"ပြန်လာတာ ဝမ်းသာပါတယ် {user['name']}!", reply_markup=get_main_kb())

@dp.message(ProfileSG.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("သင့်လိင်ကို ရွေးချယ်ပေးပါ-", reply_markup=get_gender_kb())
    await state.set_state(ProfileSG.gender)

@dp.message(ProfileSG.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await message.answer("သင့်ဓာတ်ပုံတစ်ပုံ ပို့ပေးပါ-", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ProfileSG.photo)

@dp.message(ProfileSG.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "name": data['name'],
        "gender": data['gender'],
        "photo_id": photo_id,
        "liked_users": [] }
    
    await users_col.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
    await state.clear()
    
    if GROUP_ID:
        try:
            admin_msg = (
                f"🆕 User အသစ်ရောက်လာပါပြီ\n\n"
                f"👤 အမည်: {data['name']}\n"
                f"🚻 လိင်: {data['gender']}\n"
                f"🆔 ID: {user_id}\n"
                f"🔗 Username: @{username}"
            )
            await bot.send_photo(chat_id=GROUP_ID, photo=photo_id, caption=admin_msg, parse_mode="Markdown")
        except Exception:
            pass

    await message.answer("Profile သိမ်းဆည်းပြီးပါပြီ!", reply_markup=get_main_kb())

@dp.message(F.text == "👤 ကျွန်တော့် Profile")
async def show_my_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user:
        caption = f"🏷 အမည်: {user['name']}\n🚻 လိင်: {user['gender']}\n🆔 Username: @{user['username']}"
        await message.answer_photo(user['photo_id'], caption=caption, reply_markup=get_main_kb())@dp.message(F.text == "⚙️ Profile ပြင်မယ်")
async def edit_profile(message: types.Message, state: FSMContext):
    await message.answer("Profile ပြန်ဆောက်ပါမယ်။ သင့်နာမည်ပြောပါ-", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ProfileSG.name)

@dp.message(F.text == "🔎 တခြားသူတွေရှာမယ်")
async def find_match(message: types.Message):
    pipeline = [{"$match": {"user_id": {"$ne": message.from_user.id}}}, {"$sample": {"size": 1}}]
    async for target in users_col.aggregate(pipeline):
        await message.answer_photo(
            target['photo_id'],
            caption=f"အမည်: {target['name']}\nလိင်: {target['gender']}",
            reply_markup=get_like_kb(target['user_id'])
        )
        return
    await message.answer("လူသစ်မရှိသေးပါဘူး။")

@dp.message(F.text.startswith("❤️ Like_"))
async def handle_like(message: types.Message):
    target_id = int(message.text.split("_")[1])
    me_id = message.from_user.id
    me_username = message.from_user.username or "NoUsername"

    await users_col.update_one({"user_id": me_id}, {"$addToSet": {"liked_users": target_id}})
    
    me_profile = await users_col.find_one({"user_id": me_id})
    try:
        notif_msg = f"🔔 @{me_username} က သင့်ကို Like လုပ်ထားပါတယ်။"
        await bot.send_photo(chat_id=target_id, photo=me_profile['photo_id'], caption=notif_msg)
    except Exception:
        pass

    target_user = await users_col.find_one({"user_id": target_id})
    if target_user and me_id in target_user.get("liked_users", []):
        await message.answer(f"🎉 မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! @{target_user['username']} နဲ့ စကားပြောကြည့်ပါ!")
        await bot.send_message(target_id, f"🎉 မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! @{me_username} နဲ့ စကားပြောကြည့်ပါ!")
    else:
        await message.answer("Like ပို့လိုက်ပါပြီ!")

@dp.message(F.text == "👎 Skip")
async def handle_skip(message: types.Message):
    await find_match(message)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
