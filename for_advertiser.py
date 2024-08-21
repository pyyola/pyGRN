from aiogram import Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.dispatcher import FSMContext
from config import admin_id
from keyboards import get_menu_keyboard

cancel_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_button = KeyboardButton("Отменить")
cancel_keyboard.add(cancel_button)

keyboards = get_menu_keyboard()
async def add_info_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer("Пожалуйста, отправьте ссылку на ресурс, где был прорекламирован бот:",
                         reply_markup=cancel_keyboard)
    await state.set_state("waiting_for_source_link")
    await state.update_data(user_id=user_id)

async def process_source_link(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await message.answer("Действие отменено.", reply_markup=keyboards)
        await state.finish()
        return

    source_link = message.text
    await state.update_data(source_link=source_link)
    await message.answer("Отлично! Теперь отправьте ссылку на ресурс, который вы хотите прорекламировать:")
    await state.set_state("waiting_for_advert_link")

async def process_advert_link(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await message.answer("Действие отменено.", reply_markup=keyboards)
        await state.finish()
        return

    advert_link = message.text
    await state.update_data(advert_link=advert_link)
    await message.answer("Теперь пришлите, как вы хотите подписать кнопку:")
    await state.set_state("waiting_for_button_name")

async def process_button_name(message: Message, state: FSMContext):
    if message.text == "Отменить":
        await message.answer("Действие отменено.", reply_markup=keyboards)
        await state.finish()
        return

    button_name = message.text
    await state.update_data(button_name=button_name)

    data = await state.get_data()
    user_id = data.get('user_id')
    source_link = data.get('source_link')
    advert_link = data.get('advert_link')
    button_name = data.get('button_name')

    user_name = message.from_user.username
    if not user_name:
        user_name = f"{message.from_user.first_name} {message.from_user.last_name}".strip()

    admin_message = f"🫁Пользователь с ID {user_id} (username: {user_name}) отправил следующие данные:🫁\n\n" \
                    f"Ссылка на канал рекламодателя: {source_link}\n\n" \
                    f"Ссылка на рекламируемый ресурс: {advert_link}\n\n" \
                    f"Название кнопки: {button_name}"

    for admin in admin_id:
        await message.bot.send_message(admin, admin_message)

    await message.answer("Отлично, ваш запрос принят. Ожидайте одобрения администратора.",
                         reply_markup=types.ReplyKeyboardRemove())
    await state.finish()

def register_handlers_advertiser_functions(dp: Dispatcher):
    dp.register_message_handler(add_info_command, commands=['add_info'], state="*")
    dp.register_message_handler(process_source_link, state="waiting_for_source_link")
    dp.register_message_handler(process_advert_link, state="waiting_for_advert_link")
    dp.register_message_handler(process_button_name, state="waiting_for_button_name")

