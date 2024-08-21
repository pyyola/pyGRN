from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from datetime import datetime
import random
import string
from config import dp, pusher_ids
from keyboards import get_menu_keyboard, get_cancel_keyboard
from database import get_user_state
import secrets


class PublicationForm(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_photo = State()
    waiting_for_video = State()
    waiting_for_animation = State()
    waiting_for_additional_photo = State()
    waiting_for_description = State()
    cancel_publication = State()


async def save_to_database(user_id, media_list, description):
    async with aiosqlite.connect('database.db') as db:

        async with db.execute("SELECT quantity_publication, quantity_media FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                quantity_publication = row[0]
                quantity_media = row[1]
            else:
                quantity_publication = 0
                quantity_media = 0

        quantity_publication += 1
        quantity_media += len(media_list)

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for media in media_list:
            kod = media.get('kod', '')
            media_type = media.get('type', '')

            if media_type != 'animation':
                await db.execute("""
                    INSERT INTO publication (user_id, publ_file_id, descriptions, datetime, kod, media_type, num_user_publ)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, media['file_id'], description, current_time, kod, media_type, quantity_publication))

        await db.execute("""
        UPDATE users 
        SET quantity_publication = ?, 
            quantity_media = ?
        WHERE id = ?
        """, (quantity_publication, quantity_media, user_id))

        await db.execute("""
        UPDATE use_state 
        SET state = NULL 
        WHERE id = ?
        """, (user_id,))

        await db.commit()

async def process_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.content_type != 'video':
            await dp.bot.send_message(message.chat.id, "Вы отправили не видео. Пожалуйста, отправьте видео заново.")
            return
        if 'media' not in data:
            data['media'] = []

        pusher_id = message.from_user.id in pusher_ids
        if not pusher_id and len(data['media']) >= 20:
            await dp.bot.send_message(message.chat.id, "Вы достигли максимального количества медиафайлов в публикации.")
            return

        kod = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(9))
        data['media'].append({'type': 'video', 'file_id': message.video.file_id, 'kod': kod})

        await state.update_data(data)
        await PublicationForm.waiting_for_description.set()

        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton("Не добавлять описание", callback_data='no_description')
        keyboard.add(button)

        await dp.bot.send_message(message.chat.id, "Отправьте описание публикации", reply_markup=keyboard)

async def process_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.content_type != 'photo':
            await dp.bot.send_message(message.chat.id, "Вы отправили не картинку. Пожалуйста, отправьте картинку заново.")
            return
        if 'media' not in data:
            data['media'] = []

        if 'kod' not in data:
            data['kod'] = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(9))

        pusher_id = message.from_user.id in pusher_ids
        if not pusher_id and len(data['media']) >= 20:
            await dp.bot.send_message(message.chat.id, "Вы достигли максимального количества медиафайлов в публикации.")
            return

        data['media'].append({'type': 'photo', 'file_id': message.photo[-1].file_id, 'kod': data['kod']})
        media_count = len([item for item in data['media'] if item['type'] == 'photo'])

        if media_count < 3:
            await PublicationForm.waiting_for_additional_photo.set()
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add('Да', 'Нет')
            await dp.bot.send_message(message.chat.id, f"Хотите ли вы добавить ещё одну картинку к этой публикации? ({media_count}/3)", reply_markup=markup)
        else:
            await PublicationForm.waiting_for_description.set()

            keyboard = InlineKeyboardMarkup()
            button = InlineKeyboardButton("Не добавлять описание", callback_data='no_description')
            keyboard.add(button)
            await dp.bot.send_message(message.chat.id, "Отправьте описание публикации", reply_markup=keyboard)

async def add_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        description = message.text
        if 'media' in data:
            await save_to_database(message.from_user.id, data['media'], description)
        else:
            await dp.bot.send_message(message.chat.id, "Нет медиа для сохранения.")

    await state.finish()
    menu_keyboard = get_menu_keyboard()
    await dp.bot.send_message(message.chat.id, "Публикация добавлена с описанием", reply_markup=menu_keyboard)

async def no_description_callback(query: types.CallbackQuery, state: FSMContext):
    await query.answer()
    keyboards = get_menu_keyboard()
    await query.message.reply("Сохранено без описания.", reply_markup=keyboards)
    async with state.proxy() as data:
        if 'media' in data:
            await save_to_database(query.from_user.id, data['media'], None)
        else:
            await query.message.reply("Нет медиа для сохранения.")
    await state.finish()

async def process_additional_photo_answer(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        await PublicationForm.waiting_for_photo.set()
        await dp.bot.send_message(message.chat.id, "Отправьте следующую картинку", reply_markup=types.ReplyKeyboardRemove())
    else:
        await PublicationForm.waiting_for_description.set()

        keyboard = InlineKeyboardMarkup()
        button = InlineKeyboardButton("Не добавлять описание", callback_data='no_description')
        keyboard.add(button)
        await dp.bot.send_message(message.chat.id, "Отправьте описание публикации", reply_markup=keyboard)

async def process_animation(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.content_type != 'animation':
            await dp.bot.send_message(message.chat.id,
                                      "Вы отправили не анимацию. Пожалуйста, отправьте анимацию заново.")
            return
        if 'media' not in data:
            data['media'] = []
        if len(data['media']) >= 20:
            await dp.bot.send_message(message.chat.id, "Вы достигли максимального количества медиафайлов в публикации.")
            return
        data['media'].append({'type': 'animation', 'file_id': message.animation.file_id})

        async with aiosqlite.connect('database.db') as db:

            async with db.execute("SELECT quantity_publication FROM users WHERE id = ?",
                                  (message.from_user.id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    quantity_publication = row[0]
                else:
                    quantity_publication = 0

            quantity_publication += 1

            unique_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(9))
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            await db.execute("""
                INSERT INTO publication (user_id, publ_file_id, descriptions, datetime, kod, media_type, num_user_publ)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (message.from_user.id, message.animation.file_id, None, current_time, unique_code, 'animation',
                      quantity_publication))

            await db.execute("""
            UPDATE users 
            SET quantity_publication = quantity_publication + 1, 
                quantity_media = quantity_media + 1
            WHERE id = ?
            """, (message.from_user.id,))

            await db.execute("""
            UPDATE use_state 
            SET state = NULL 
            WHERE id = ?
            """, (message.from_user.id,))

            await db.commit()

        await state.finish()

        menu_keyboard = get_menu_keyboard()
        await dp.bot.send_message(message.chat.id, "Публикация добавлена", reply_markup=menu_keyboard)

async def ask_publication_type(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('database.db') as db:
        async with db.execute("SELECT banned, quantity_media, quantity_referals FROM users WHERE id = ?",
                              (message.from_user.id,)) as cursor:
            user_data = await cursor.fetchone()

            if user_data:
                banned, quantity_media, quantity_referals = user_data

                if banned == 1:
                    await dp.bot.send_message(message.chat.id, "Вы забанены и не можете публиковать.")
                    return

                async with db.execute("SELECT quantity_publ FROM advertiser WHERE id = ?", (message.from_user.id,)) as cursor_adv:
                    advertiser_data = await cursor_adv.fetchone()

                if advertiser_data:
                    quantity_publ = advertiser_data[0]
                    max_media = quantity_publ
                else:
                    if quantity_referals >= 5:
                        max_media = 100
                    elif quantity_referals >= 3:
                        max_media = 70
                    elif quantity_referals >= 1:
                        max_media = 50
                    else:
                        max_media = 30

                pusher_id = message.from_user.id in pusher_ids

                if not pusher_id and quantity_media >= max_media:
                    await dp.bot.send_message(message.chat.id,
                                              f"Увы, но вы не можете публиковать медиа. Ваш максимум: {max_media} медиафайлов.\n\nПригласите друзей либо подпишитесь на канал, чтобы повысить лимит.")
                else:
                    sticker_id = 'CAACAgIAAxkBAAEMSbBmaH2Z41BKPcG57X_l54DifTb1SQACRgMAArVx2gbyolHjVhMwjDUE'
                    await dp.bot.send_sticker(message.chat.id, sticker_id)

                    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    markup.add('🎥 Видео', '🏞️ Фото', '🎞 GIF')
                    markup.add('Отменить публикацию')

                    await PublicationForm.waiting_for_confirmation.set()
                    await dp.bot.send_message(message.chat.id, "Что вы хотите опубликовать?", reply_markup=markup)

                    await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                                     (message.from_user.id, 'ask_publication_type'))
                    await db.commit()


async def process_publication_type(message: types.Message, state: FSMContext):
    cancel_keyboard =get_cancel_keyboard()
    publication_type = message.text.lower()
    if publication_type == '🎥 видео':
        await PublicationForm.waiting_for_video.set()
        await dp.bot.send_message(message.chat.id, "Отправьте видео", reply_markup=cancel_keyboard)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, 'waiting_video'))
            await db.commit()

    elif publication_type == '🏞️ фото':
        await PublicationForm.waiting_for_photo.set()
        await dp.bot.send_message(message.chat.id, "Отправьте картинку", reply_markup=cancel_keyboard)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, 'waiting_photo'))
            await db.commit()

    elif publication_type == '🎞 gif':
        await PublicationForm.waiting_for_animation.set()
        await dp.bot.send_message(message.chat.id, "Отправьте GIF", reply_markup=cancel_keyboard)

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, 'waiting_animation'))
            await db.commit()

    elif publication_type == 'отменить публикацию':
        await cancel_adding_publication(message, state)
async def cancel_adding_publication(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    keyboards = get_menu_keyboard()
    current_state = await state.get_state()
    user_state = await get_user_state(user_id)

    async with aiosqlite.connect('database.db') as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT state FROM use_state WHERE id = ?', (user_id,)) as cursor:
            user_db_state = await cursor.fetchone()

        if user_db_state and user_db_state['state'] == 'ask_publication_type':
            await dp.bot.send_message(message.chat.id, "Процесс добавления публикации был отменён.", reply_markup=keyboards)
            await state.finish()
            await db.execute('UPDATE use_state SET state = NULL WHERE id = ?', (user_id,))
            await db.commit()
            return

        if current_state in (PublicationForm.waiting_for_confirmation.state,
                             PublicationForm.waiting_for_photo.state,
                             PublicationForm.waiting_for_video.state,
                             PublicationForm.waiting_for_animation.state):
            await state.finish()
            await dp.bot.send_message(message.chat.id, "Процесс добавления публикации был отменён.", reply_markup=keyboards)
        elif user_state in ('waiting_photo', 'waiting_video', 'waiting_animation'):
            await message.reply("Бот был перезапущен, не удалось ничего опубликовать.", reply_markup=keyboards)

        await db.execute('UPDATE use_state SET state = NULL WHERE id = ?', (user_id,))
        await db.commit()



async def cancel_photo_upload(message: types.Message, state: FSMContext):
    await state.finish()
    menu_keyboard = get_menu_keyboard()
    await dp.bot.send_message(message.chat.id, "Процесс добавления публикации был отменён.", reply_markup=menu_keyboard)
async def undefined_additional_photo_answer(message: types.Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add('Да', 'Нет')
    await dp.bot.send_message(message.chat.id, "Пожалуйста, ответьте 'Да' или 'Нет'.", reply_markup=markup)


async def generate_unique_code(length=9):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def handle_wrong_content_type_video(message: types.Message, state: FSMContext):
    if message.text == "Отменить публикацию":
        await cancel_adding_publication(message, state)
    else:
        await dp.bot.send_message(message.chat.id, "Вы отправили не видео. Пожалуйста, отправьте видео заново.", reply_markup=get_cancel_keyboard())

async def handle_wrong_content_type_animation(message: types.Message, state: FSMContext):
    if message.text == "Отменить публикацию":
        await cancel_adding_publication(message, state)
    else:
        await dp.bot.send_message(message.chat.id, "Вы отправили не GIF. Пожалуйста, отправьте анимацию заново.", reply_markup=get_cancel_keyboard())

async def handle_wrong_content_type(message: types.Message, state: FSMContext):
    if message.text == "Отменить публикацию":
        await cancel_adding_publication(message, state)
    else:
        await dp.bot.send_message(message.chat.id, "Вы отправили не картинку. Пожалуйста, отправьте картинку заново.", reply_markup=get_cancel_keyboard())

def register_handlers_add_publication(dp: Dispatcher):
    dp.register_message_handler(ask_publication_type, lambda message: '🎬Опубликовать🌟' in message.text)
    dp.register_message_handler(process_publication_type, state=PublicationForm.waiting_for_confirmation)
    dp.register_message_handler(process_photo, content_types=types.ContentType.PHOTO,state=PublicationForm.waiting_for_photo)
    dp.register_message_handler(process_video, content_types=types.ContentType.VIDEO,state=PublicationForm.waiting_for_video)
    dp.register_message_handler(process_animation, content_types=types.ContentType.ANIMATION,state=PublicationForm.waiting_for_animation)
    dp.register_message_handler(process_additional_photo_answer, lambda message: message.text in ['Да', 'Нет'],state=PublicationForm.waiting_for_additional_photo)
    dp.register_message_handler(undefined_additional_photo_answer, lambda message: True,state=PublicationForm.waiting_for_additional_photo)
    dp.register_message_handler(cancel_adding_publication, state=PublicationForm.cancel_publication)
    dp.register_message_handler(handle_wrong_content_type_video, state=PublicationForm.waiting_for_video)
    dp.register_message_handler(handle_wrong_content_type_animation, state=PublicationForm.waiting_for_animation)
    dp.register_message_handler(handle_wrong_content_type, state=PublicationForm.waiting_for_photo)
    dp.register_message_handler(cancel_adding_publication, state="*", text="Отменить публикацию")
    dp.register_callback_query_handler(no_description_callback, lambda query: query.data == 'no_description',state=PublicationForm.waiting_for_description)
    dp.register_message_handler(process_video, content_types=types.ContentType.VIDEO,state=PublicationForm.waiting_for_video)
    dp.register_message_handler(add_description, state=PublicationForm.waiting_for_description)
