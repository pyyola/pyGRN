from aiogram import types
from database import create_connection, create_tables, add_user, user_exists
from keyboards import get_menu_keyboard
from config import DATABASE

async def start_command(message: types.Message):
    conn = await create_connection(DATABASE)
    await create_tables(conn)

    user_id = message.from_user.id
    username = message.from_user.username or "No username"

    if not await user_exists(conn, user_id):
        await add_user(conn, user_id, username)
        message_text = ("Привет! Благодарим вас за выбор нашего бота. Пожалуйста, прочитайте и примите все условия, указанные в этом соглашении, нажав кнопку ниже. Нажимая эту кнопку или продолжая использовать бота без нажатия на кнопку, вы принимаете все условия, указанные в соглашении.\n"
                        "https://telegra.ph/usloviya-soglasheniya-04-27")
        reply_markup = types.InlineKeyboardMarkup(row_width=1)
        reply_markup.add(types.InlineKeyboardButton(text="Принять условия", callback_data="accept_conditions"))
        await message.bot.send_message(chat_id=message.chat.id, text=message_text, reply_markup=reply_markup)
    else:
        keyboard = get_menu_keyboard()
        await message.bot.send_message(chat_id=message.chat.id, text="Выберите действие:", reply_markup=keyboard)
    await conn.close()

async def on_accept_conditions(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.delete()
    await callback_query.message.bot.send_sticker(callback_query.message.chat.id, sticker="CAACAgIAAxkBAAEMSaRmaHtwWGsY3Mjkj3We_zNKEIZEIgACRQMAArVx2gaTiBAcidwNGzUE", reply_markup=get_menu_keyboard())

def register_handlers_start(dp):
    dp.register_message_handler(start_command, commands=['start'])
    dp.register_callback_query_handler(on_accept_conditions, text="accept_conditions")

