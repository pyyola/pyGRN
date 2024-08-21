from aiogram import types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton , InlineKeyboardButton , InlineKeyboardMarkup
from config import bot, admin_id

def get_inline_keyboard():
    inline_markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("Мой профиль 👨‍💼📋", callback_data="button_1"),
        InlineKeyboardButton("Новости 📰📢", callback_data="button_2"),
        InlineKeyboardButton("Рейтинг 🏆🍇", callback_data="button_3"),
        InlineKeyboardButton("Мои публикации ✍️📚", callback_data="button_4"),
        InlineKeyboardButton("Реферальная программа 👥🔄", callback_data="button_5"),
    ]

    inline_markup.add(buttons[0])
    inline_markup.row(buttons[1], buttons[2])
    inline_markup.add(buttons[3])
    inline_markup.add(buttons[4])
    return inline_markup

def get_menu_keyboard(is_admin=False):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        KeyboardButton(text="📁 Меню 📋")
    ]
    keyboard.add(*buttons)
    buttons_row = [
        KeyboardButton(text="🎬Опубликовать🌟"),
        KeyboardButton(text="📺Лента публикаций🎭")
    ]
    keyboard.row(*buttons_row)

    return keyboard

async def menu_command(message: types.Message):
    is_admin = message.from_user.id in admin_id
    keyboard = get_menu_keyboard(is_admin)
    await bot.send_sticker(chat_id=message.chat.id, sticker="CAACAgIAAxkBAAEMSaZmaHwv6RiQxinOBQP0iGrsvpa_xQACSgMAArVx2gbCfgb6m0gexDUE", reply_markup=keyboard)

def get_cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Отменить публикацию')
    return markup

def get_reaction_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["❤️", "👎", "жалоба","💤"]
    keyboard.row(*buttons)
    return keyboard

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(menu_command, commands=['menu'])

def get_admin_keyboard():
    buttons = [
        ["Эст", "Муз", "Юмор"],
        ["Малол", "Празд", "Спорт"],
        ["Машины", "Мотива", "Кринж"],
        ["Жиза", "💤", "хуйня"]
    ]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for row in buttons:
        keyboard.add(*[types.KeyboardButton(text=btn) for btn in row])
    return keyboard