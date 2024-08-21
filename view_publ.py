from aiogram import Dispatcher
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import StatesGroup, State
from config import bot, admin_id
import aiosqlite
import random
from keyboards import get_reaction_keyboard, get_admin_keyboard, get_menu_keyboard
from aiogram import types
from aiogram.dispatcher import FSMContext
from database import get_subscription_status, update_subscription_status
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


class PublicationState(StatesGroup):
    ViewingPublications = State()


async def send_media_with_description(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect('database.db') as db:
        if user_id in admin_id:
            cursor = await db.execute(
                'SELECT id, kod, media_type, publ_file_id, descriptions, popularity FROM publication WHERE theme_media IS NULL ORDER BY popularity DESC'
            )
        else:
            cursor = await db.execute(
                'SELECT id, kod, media_type, publ_file_id, descriptions, popularity FROM publication WHERE user_id != ? ORDER BY popularity DESC',
                (user_id,)
            )
        media_items = await cursor.fetchall()

        if media_items:
            await PublicationState.ViewingPublications.set()

            if user_id in admin_id:
                keyboard = get_admin_keyboard()
            else:
                keyboard = get_reaction_keyboard()

            await bot.send_sticker(
                chat_id=message.chat.id,
                sticker="CAACAgIAAxkBAAEMSapmaHyzk-hQLJ_qNEV_cKgvFf0TdwACUwMAArVx2gbtH-L5lSdj5DUE",
                reply_markup=keyboard
            )

            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                             (user_id, 'showing_publication'))
            await db.commit()
            await send_next_publication(message, state)
        else:
            await bot.send_message(message.chat.id, "Публикаций пока нет.")


async def send_next_publication(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ad_shows = data.get('ad_shows', 0)
    user_id = message.from_user.id
    keyboards = get_menu_keyboard()

    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT favorite_theme, subscrib_chnl, narrow_theme FROM users WHERE id = ?', (user_id,)) as cursor:
            user_info = await cursor.fetchone()

        favorite_theme = user_info[0] if user_info else 'random'
        subscrib_chnl = user_info[1] if user_info else 'false'
        narrow_theme = user_info[2] if user_info else None

        await state.update_data(narrow_theme=narrow_theme)

        if ad_shows > 30 and random.randint(1, 100) <= 10:
            if subscrib_chnl != 'true':
                await send_advertisement(user_id, message, state)
                return
            else:
                await send_next_publication(message, state)
                return

        publication_query = ''
        query_params = ()
        if user_id in admin_id:
            publication_query = '''
                SELECT id, kod, publ_file_id, descriptions, popularity, media_type, user_id
                FROM publication 
                WHERE theme_media IS NULL
                ORDER BY popularity DESC
            '''
            query_params = ()
        else:
            if narrow_theme:
                publication_query = '''
                    SELECT id, kod, publ_file_id, descriptions, popularity, media_type, user_id
                    FROM publication 
                    WHERE user_id != ? AND kod NOT IN (SELECT kod FROM users_viewed_publications WHERE id = ?) 
                    AND theme_media = ? 
                    ORDER BY popularity DESC
                '''
                query_params = (user_id, user_id, narrow_theme)

                cursor = await db.execute(publication_query, query_params)
                media_items = await cursor.fetchall()

                if not media_items:
                    narrow_theme = None

            if not narrow_theme:
                if favorite_theme == 'random':
                    publication_query = '''
                        SELECT id, kod, publ_file_id, descriptions, popularity, media_type, user_id
                        FROM publication 
                        WHERE user_id != ? AND kod NOT IN (SELECT kod FROM users_viewed_publications WHERE id = ?) 
                        ORDER BY popularity DESC
                    '''
                    query_params = (user_id, user_id)
                else:
                    theme_filter = {
                        'humor': ('Малол', 'Празд', 'Юмор', 'Кринж', 'Жиза'),
                        'aesthetics': ('Эст', 'Муз', 'Машины'),
                        'sport': ('Спорт',)
                    }.get(favorite_theme, ('random',))
                    placeholders = ','.join('?' for _ in theme_filter)
                    publication_query = f'''
                        SELECT id, kod, publ_file_id, descriptions, popularity, media_type, user_id
                        FROM publication 
                        WHERE user_id != ? AND kod NOT IN (SELECT kod FROM users_viewed_publications WHERE id = ?) 
                        AND theme_media IN ({placeholders}) 
                        ORDER BY popularity DESC
                    '''
                    query_params = (user_id, user_id, *theme_filter)

                cursor = await db.execute(publication_query, query_params)
                media_items = await cursor.fetchall()

                if not media_items:
                    publication_query = '''
                        SELECT id, kod, publ_file_id, descriptions, popularity, media_type, user_id
                        FROM publication 
                        WHERE user_id != ? AND kod NOT IN (SELECT kod FROM users_viewed_publications WHERE id = ?) 
                        ORDER BY popularity DESC
                    '''
                    query_params = (user_id, user_id)

        cursor = await db.execute(publication_query, query_params)
        media_items = await cursor.fetchall()

        if not media_items:
            if user_id in admin_id:
                await bot.send_message(message.chat.id, "Увы, публикации для администраторов закончились.", reply_markup=keyboards)
                await state.finish()
            else:
                await bot.send_message(message.chat.id, "Увы, новых публикаций ещё нет.", reply_markup=keyboards)
                await state.finish()
            return

        if media_items and all(len(item) >= 7 for item in media_items):
            total_popularity = sum(item[4] for item in media_items)
            random_num = random.uniform(0, total_popularity)
            cumulative_popularity = 0
            await state.update_data(ad_shows=ad_shows + 1)

            selected_item = None

            for item in media_items:
                if len(item) >= 7:
                    cumulative_popularity += item[4]
                    if cumulative_popularity >= random_num:
                        selected_item = item
                        break
            if selected_item:
                publication_id, kod, publ_file_id, description, popularity, media_type, publication_user_id = selected_item
                await state.update_data(current_publication_id=publication_id, current_publication_kod=kod)

                cursor = await db.execute('SELECT link, button_name FROM advertiser WHERE id = ?', (publication_user_id,))
                advertiser_info = await cursor.fetchone()

                if advertiser_info and media_type in ['video', 'photo']:
                    link, button_name = advertiser_info
                    inline_button = types.InlineKeyboardMarkup()
                    inline_button.add(types.InlineKeyboardButton(text=button_name, url=link))
                else:
                    inline_button = None

                try:
                    if media_type == 'video':
                        await bot.send_video(message.chat.id, video=publ_file_id, caption=description, reply_markup=inline_button)
                    elif media_type == 'animation':
                        await bot.send_animation(message.chat.id, animation=publ_file_id, caption=description)
                    elif media_type == 'photo':
                        cursor = await db.execute('SELECT publ_file_id, descriptions FROM publication WHERE kod = ? AND media_type = "photo"', (kod,))
                        photos = await cursor.fetchall()

                        if len(photos) == 1:
                            await bot.send_photo(message.chat.id, photo=photos[0][0], caption=description, reply_markup=inline_button)
                        elif 2 <= len(photos) <= 10:
                            photo_ids = [types.InputMediaPhoto(photo[0], caption=(description if i == 0 else '')) for i, photo in enumerate(photos)]
                            await bot.send_media_group(message.chat.id, photo_ids)
                        else:
                            await bot.send_message(message.chat.id, "Не удалось найти подходящие фотографии для публикации.")
                    else:
                        pass

                    if user_id in admin_id:
                        await db.execute('INSERT OR IGNORE INTO admin_viewed_publications (kod) VALUES (?)', (kod,))
                    else:
                        await db.execute('INSERT OR IGNORE INTO users_viewed_publications (id, kod) VALUES (?, ?)', (user_id, kod))
                    await db.commit()
                except Exception as e:
                    pass
            else:
                if user_id in admin_id:
                    await bot.send_message(message.chat.id, "Увы, публикации для администраторов закончились.", reply_markup=keyboards)
                    await state.finish()
                else:
                    await bot.send_message(message.chat.id, "Увы, новых публикаций ещё нет.", reply_markup=keyboards)
                    await state.finish()
        else:
            if user_id in admin_id:
                await bot.send_message(message.chat.id, "Увы, публикации для администраторов закончились.", reply_markup=keyboards)
                await state.finish()
            else:
                await bot.send_message(message.chat.id, "Увы, новых публикаций ещё нет.", reply_markup=keyboards)
                await state.finish()

async def handle_admin_response(message: types.Message, state: FSMContext):
    if message.from_user.id in admin_id:
        theme = message.text
        async with state.proxy() as data:
            publication_kod = data.get('current_publication_kod')

            async with aiosqlite.connect('database.db') as db:
                await db.execute(
                    'UPDATE publication SET theme_media = ? WHERE kod = ?',
                    (theme, publication_kod)
                )

                await db.commit()
            await send_next_publication(message, state)
async def send_advertisement(user_id: int, message: types.Message, state: FSMContext):
    is_subscribed = await get_subscription_status(user_id)

    if not is_subscribed:
        not_interested_button = KeyboardButton("Не интересует")
        just_subscribed_button = KeyboardButton("Проверить подписку")
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True).add(not_interested_button, just_subscribed_button)

        await bot.send_sticker(
            user_id,
            "CAACAgIAAxkBAAEMNEpmU5FF46ulJvCiLGNBE6gcZaVX8AACggUAAtJaiAG9YsVO2EFWOzUE",
            reply_markup=keyboard
        )

        advertisement_text = (
            "Подпишитесь на наш канал!\n\n"
            "Преимущества подписки:\n"
            "- <b>Нету рекламы.</b>\n\n"
            "- <b>Ваши публикации продвигаются быстрее.</b>\n\n"
            "- <b>Увеличенный лимит добавления публикаций.</b>\n\n"
            "- <b>Возможность легко следить за новостями и просматривать самые популярные публикации, "
            "собравшие лучшую статистику в течение дня.</b>"
        )

        subscribe_button = InlineKeyboardButton("Подписаться", url="https://t.me/+N5G8TDEL4jExMDQy")
        inline_keyboard = InlineKeyboardMarkup().add(subscribe_button)

        await bot.send_message(
            user_id,
            advertisement_text,
            reply_markup=inline_keyboard,
            parse_mode="HTML"
        )
        await state.update_data(ad_shows=0)
    else:
        await send_next_publication(message, state)

async def not_interested(message: types.Message, state: FSMContext):
    sticker_id = 'CAACAgIAAxkBAAEMSbRmaIEdMYg8gzSk1CUE1RhwsEMNagACVwMAArVx2ga2e7f7gIXrkjUE'
    await bot.send_sticker(message.chat.id, sticker_id)

    await update_subscription_status(message.from_user.id, False)
    await message.reply("жаль, может в следующий раз)?")
    await send_media_with_description(message, state)
async def just_subscribed(message: types.Message, state: FSMContext):
    is_subscribed = await get_subscription_status(message.from_user.id)
    if is_subscribed:
        sticker_id = 'CAACAgIAAxkBAAEMSbZmaIGBGJxhHEzx3PVnA0wG2Ck8oQACQwMAArVx2gZYvRa_g3e_xzUE'
        await bot.send_sticker(message.chat.id, sticker_id)
        await message.answer("спасибо, что подписались на наш канал, буст начал действовать от этой минуты!\n теперь никакой рекламы 🫦💞")
        await send_media_with_description(message, state)
    else:
        sticker_id = 'CAACAgIAAxkBAAEMSbJmaIEMBvcZdlesJ44CmA6jZ37dPwACUQMAArVx2gat6tu-HeOH2zUE'
        await bot.send_sticker(message.chat.id, sticker_id)
        await message.answer("вы так и не подписались, попробуете в следующий раз ")
        await send_media_with_description(message, state)

def register_handlers_view_publications(dp: Dispatcher):
    dp.register_message_handler(send_media_with_description, Text(equals="📺Лента публикаций🎭"), state='*')
    dp.register_message_handler(not_interested, Text(equals="Не интересует"),
                                state=PublicationState.ViewingPublications)
    dp.register_message_handler(handle_admin_response,
                                lambda message: message.text in ["Эст", "Муз", "Юмор", "Малол", "Празд", "Спорт",
                                                                 "Машины", "Мотива", "Кринж", "Жиза" , "хуйня"],
                                state=PublicationState.ViewingPublications)
    dp.register_message_handler(just_subscribed, Text(equals="Проверить подписку🦷"),
                                state=PublicationState.ViewingPublications)
