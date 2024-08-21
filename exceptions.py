from database import get_user_state
from aiogram import Dispatcher, types
from aiogram.types import ContentType
import aiosqlite
from add_publication import PublicationForm
from keyboards import get_menu_keyboard

async def unknown_video(message: types.Message):
    user_id = message.from_user.id

    user_state = await get_user_state(user_id)

    if user_state != PublicationForm.waiting_for_video.state and message.content_type == ContentType.VIDEO and user_state in ('waiting_video'):
        keyboards =get_menu_keyboard()
        await message.reply("Бот был перезапущен, не удалось ничего опубликовать.", reply_markup=keyboards)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, None))
            await db.commit()
    else:
        pass

async def unknown_photo(message: types.Message):
    user_id = message.from_user.id

    user_state = await get_user_state(user_id)

    if user_state != PublicationForm.waiting_for_photo.state and message.content_type == ContentType.PHOTO and user_state == 'waiting_photo':
        keyboards = get_menu_keyboard()
        await message.reply("Бот был перезапущен, не удалось ничего опубликовать.", reply_markup=keyboards)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, None))
            await db.commit()
    else:
        pass

async def unknown_animation(message: types.Message):
    user_id = message.from_user.id

    user_state = await get_user_state(user_id)

    if user_state != PublicationForm.waiting_for_animation.state and message.content_type == ContentType.ANIMATION and user_state == 'waiting_animation':
        keyboards = get_menu_keyboard()
        await message.reply("Бот был перезапущен, не удалось ничего опубликовать.", reply_markup=keyboards)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, None))
            await db.commit()
    else:
        pass

def register_handlers_exceptions(dp: Dispatcher):
    dp.register_message_handler(unknown_video, content_types=ContentType.VIDEO)
    dp.register_message_handler(unknown_photo, content_types=ContentType.PHOTO)
    dp.register_message_handler(unknown_animation, content_types=ContentType.ANIMATION)
