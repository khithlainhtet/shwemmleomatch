import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient

# --- Configuration ---
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

def get_inline_like_kb(target_id):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Like", callback_data=f"like_{target_id}"),
            InlineKeyboardButton(text="👎 Skip", callback_data="skip_next")
        ]
    ])
    return builder

# --- Handlers ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = await users_col.find_one({"user_id": message.from_user.id})
    if not user:
        await message.answer("မြန်မာ အချစ်/မိတ်ဆွေရှာမယ် Bot ကနေ ကြိုဆိုလိုက်ပါတယ် 💞။ Profile အရင်ဆောက်ရအောင်! သင့်နာမည် ဘယ်လိုခေါ်လဲ?", reply_markup=ReplyKeyboardRemove())
        await state.set_state(ProfileSG.name)
    else:
        await message.answer(f"ပြန်လာတာ ဝမ်းသာပါတယ် {user['name']}!", reply_markup=get_main_kb())

@dp.message(F.text == "⚙️ Profile ပြင်မယ်")
async def edit_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Profile ကို အသစ်ပြန်ဆောက်ပါမယ်။ သင့်နာမည်ကို အရင်ပြောပေးပါ-", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ProfileSG.name)

@dp.message(ProfileSG.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("သင့်လိင်ကို ရွေးချယ်ပေးပါ-", reply_markup=get_gender_kb())
    await state.set_state(ProfileSG.gender)

@dp.message(ProfileSG.gender)
async def process_gender(message: types.Message, state: FSMContext):
    if message.text not in ["ယောကျာ်း", "မိန်းမ"]:
        await message.answer("ခလုတ်ကို အသုံးပြု၍ ရွေးချယ်ပေးပါ-", reply_markup=get_gender_kb())
        return
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
        "liked_users": []
    }
    
    await users_col.update_one({"user_id": user_id}, {"$set": user_data}, upsert=True)
    await state.clear()
    
    if GROUP_ID:
        try:
            admin_msg = f"🆕 User အသစ်\n👤 {data['name']}\n🚻 {data['gender']}\n🆔 {user_id}\n🔗 @{username}"
            await bot.send_photo(chat_id=GROUP_ID, photo=photo_id, caption=admin_msg)
        except: 
            pass

    await message.answer("Profile သိမ်းဆည်းပြီးပါပြီ!", reply_markup=get_main_kb())

    @dp.message(F.text == "🔎 တခြားသူတွေရှာမယ်")
async def find_match(message: types.Message):
    my_id = message.from_user.id
async def find_match(message: types.Message):
    my_id = message.from_user.id
    total_users = await users_col.count_documents({"user_id": {"$ne": my_id}})
    
    if total_users == 0:
        await message.answer("လက်ရှိမှာ လူသစ်မရှိသေးပါဘူး။")

@dp.message(F.text == "🔎 တခြားသူတွေရှာမယ်")
    await message.answer("Profile သိမ်းဆည်းပြီးပါပြီ!", reply_markup=get_main_kb())@dp.message(F.text == "🔎 တခြားသူတွေရှာမယ်")
async def find_match(message: types.Message):
    my_id = message.from_user.id
   
    # Database ထဲမှာ ကိုယ်မဟုတ်တဲ့သူ ရှိမရှိ စစ်ဆေးခြင်း
    total_users = await users_col.count_documents({"user_id": {"$ne": my_id}})
    if total_users == 0:
        await message.answer("လက်ရှိမှာ လူသစ်မရှိသေးပါဘူး။ တခြားသူတွေ Profile ဆောက်တာကို စောင့်ပေးပါဗျ။")
        return

    pipeline = [
        {"$match": {"user_id": {"$ne": my_id}}},
        {"$sample": {"size": 1}}
    ]
    # လူရှိမရှိ စစ်ဆေးခြင်း
    total_users = await users_col.count_documents({"user_id": {"$ne": my_id}})
    
    if total_users == 0:
        await message.answer("လက်ရှိမှာ လူသစ်မရှိသေးပါဘူး။")
        return

    pipeline = [
        {"$match": {"user_id": {"$ne": my_id}}},
        {"$sample": {"size": 1}}
    ]
    
    async for target in users_col.aggregate(pipeline):
        await message.answer_photo(
            target['photo_id'],
            caption=f"အမည်: {target['name']}\nလိင်: {target['gender']}",
            reply_markup=get_inline_like_kb(target['user_id'])
        )
            reply_markup=get_inline_like_kb(target['user_id']))
        
        break
    if not found:
        await message.answer("လူသစ်မရှိသေးပါဘူး။")

@dp.message(F.text == "👤 ကျွန်တော့် Profile")
async def show_my_profile(message: types.Message):
    user = await users_col.find_one({"user_id": message.from_user.id})
    if user:
        await message.answer_photo(user['photo_id'], caption=f"🏷 အမည်: {user['name']}\n🚻 လိင်: {user['gender']}\n🆔 @{user['username']}")

@dp.callback_query(F.data.startswith("like_"))
async def handle_inline_like(callback: types.CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    me_id = callback.from_user.id
    me_username = callback.from_user.username or "NoUsername"

    await users_col.update_one({"user_id": me_id}, {"$addToSet": {"liked_users": target_id}})
    me_profile = await users_col.find_one({"user_id": me_id})
    
    try:
        me_label = f"@{me_username}" if me_username != "NoUsername" else f"[{me_profile['name']}](tg://user?id={me_id})"

        await bot.send_photo(chat_id=target_id, photo=me_profile['photo_id'], 
                             caption=f"🔔 {me_label} က သင့်ကို Like လုပ်ထားပါတယ်။", parse_mode="Markdown")
    except: 
        pass
        m_link = f"@{me_username}" if me_username != "NoUsername" else f"[{me_profile['name']}](tg://user?id={me_id})"
        await bot.send_photo(chat_id=target_id, photo=me_profile['photo_id'], 
                             caption=f"🔔 {me_label} က သင့်ကို Like လုပ်ထားပါတယ်။", parse_mode="Markdown")
    except: 
        pass

    target_user = await users_col.find_one({"user_id": target_id})
    if target_user and me_id in target_user.get("liked_users", []):

        t_link = f"@{target_user['username']}" if target_user['username'] != "NoUsername" else f"[{target_user['name']}](tg://user?id={target_id})"
        m_link = f"@{me_username}" if me_username != "NoUsername" else f"[{me_profile['name']}](tg://user?id={me_id})"

        await callback.message.answer(f"🎉မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! {t_link} နဲ့ စကားပြောကြည့်ပါ!", parse_mode="Markdown")
        if me_username != "NoUsername":
            me_link = f"@{me_username}"
        else:
            me_link = f"[{me_profile['name']}](tg://user?id={me_id})"
            
        notif_txt = f"🔔 {me_link} က သင့်ကို Like လုပ်ထားပါတယ်။"
        await bot.send_photo(chat_id=target_id, photo=me_profile['photo_id'], caption=notif_txt, parse_mode="Markdown")
    except: pass

    # ၂။ Match ဖြစ်မဖြစ် စစ်ဆေးမယ်
    target_user = await users_col.find_one({"user_id": target_id})
    if target_user and me_id in target_user.get("liked_users", []):
        t_label = f"@{target_user['username']}" if target_user['username'] != "NoUsername" else f"[{target_user['name']}](tg://user?id={target_id})"
        m_label = f"@{me_username}" if me_username != "NoUsername" else f"[{me_profile['name']}](tg://user?id={me_id})"

        await callback.message.answer(f"🎉 မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! {t_label} နဲ့ စကားပြောကြည့်ပါ!", parse_mode="Markdown")
        await bot.send_message(target_id, f"🎉 မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! {m_label} နဲ့ စကားပြောကြည့်ပါ!", parse_mode="Markdown")

        t_link = f"@{target_user['username']}" if target_user['username'] != "NoUsername" else f"[{target_user['name']}](tg://user?id={target_id})"
      
        # Username မရှိလည်း တိုက်ရိုက်စကားပြောလို့ရမည့် Link များ
        t_name = target_user['name']
        t_link = f"@{target_user['username']}" if target_user['username'] != "NoUsername" else f"[{t_name}](tg://user?id={target_id})"
        m_link = f"@{me_username}" if me_username != "NoUsername" else f"[{me_profile['name']}](tg://user?id={me_id})"

        await callback.message.answer(f"🎉 မိတ်ဆွေ/သူငယ်ချင်း ဖြစ်သွားပါပြီ! {t_link} နဲ့ စကားပြောကြည့်ပါ!", parse_mode="Markdown")
        await bot.send_message(target_id, f"🎉မိတ်ဆွေ/သူငယ်ချင်း  ဖြစ်သွားပါပြီ! {m_link} နဲ့ စကားပြောကြည့်ပါ!", parse_mode="Markdown")
    else:
        await callback.answer("Like ပို့လိုက်ပါပြီ!", show_alert=False)
    
    await callback.message.delete()
    await find_match(callback.message)

@dp.callback_query(F.data == "skip_next")
async def handle_inline_skip(callback: types.CallbackQuery):
    await callback.message.delete()
    await find_match(callback.message)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())