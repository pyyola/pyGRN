from aiogram.dispatcher import FSMContext
import datetime
from database import get_top_5_users_with_most_likes, get_user_data, get_latest_news_from_db, get_subscrib_chnl_from_db, get_subscription_status, update_subscription_status, get_user_count
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite
from config import bot
from keyboards import get_inline_keyboard

async def show_latest_news(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    latest_news_text = await get_latest_news_from_db()

    user_id = callback_query.from_user.id
    subscrib_chnl = await get_subscrib_chnl_from_db(user_id)

    if subscrib_chnl == "true":

        latest_news = f"<b>{latest_news_text}</b>"
        inline_keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
        )
    else:
        advertisement_text = (
            "<b>🔔 Подпишитесь на наш канал для следующих преимуществ:</b>\n\n"
            "- <b>Нету рекламы.</b>\n"
            "- <b>Ваши публикации продвигаются быстрее.</b>\n"
            "- <b>Увеличенный лимит добавления публикаций.</b>"
        )

        latest_news = f"<b>{latest_news_text}</b>\n\n{advertisement_text}"

        subscribe_button = InlineKeyboardButton("Подписаться на канал", url="https://t.me/prosto_pai")

        inline_keyboard = InlineKeyboardMarkup().add(
            subscribe_button
        ).add(
            InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
        )

    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=latest_news,
        reply_markup=inline_keyboard,
        parse_mode='HTML'
    )

async def handle_news_button(callback_query: types.CallbackQuery, state: FSMContext):
    await show_latest_news(callback_query, state)

async def main_panel(message: types.Message):
    inline_keyboard = get_inline_keyboard()
    with open('images/image.jpg', 'rb') as photo:
        await bot.send_photo(message.chat.id, photo, caption="", reply_markup=inline_keyboard)

async def process_input_promo_code(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    async with aiosqlite.connect('database.db') as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT valid_promo FROM users WHERE id=?", (user_id,))
        user_valid_promo = await cursor.fetchone()

    if user_valid_promo and user_valid_promo[0] == 0:
        await bot.send_message(user_id, "Вы уже активировали промокод ранее.")

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, None))
            await db.commit()
    else:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        await bot.send_message(user_id, "Отправьте промокод")
        await state.set_state("waiting_for_promo_code")

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, 'waiting_promo'))
            await db.commit()


async def show_referral_program(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_id = callback_query.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        referral_text = (
            "<b>Ваш уникальный промокод:</b> <code>{}</code>\n\n"
            "<b>Как использовать промокод:</b>\n"
            "1. Передайте его другу.\n"
            "2. Друг должен зайти в бот в первый день после запуска.\n"
            "3. Нажмите 'Реферальная программа👥' -> 'Ввести промокод'.\n"
            "4. Введите ваш промокод на аккаунте друга.\n\n"
            "<b>Важно потому что:</b>\n"
            "- Нету рекламы.\n"
            "- Быстрое продвижение публикаций.\n"
            "- Увеличенный лимит добавления публикаций.\n"
        ).format(user_data[8])

        inline_keyboard = InlineKeyboardMarkup()

        user_registration_time = datetime.datetime.strptime(user_data[2], "%Y-%m-%d %H:%M:%S")
        current_time = datetime.datetime.now()
        time_difference = current_time - user_registration_time

        if user_data[9] != 0 and time_difference.days < 1:
            inline_keyboard.add(
                InlineKeyboardButton("Ввести промокод", callback_data="input_promo_code")
            )

        inline_keyboard.row(
            InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
        )

        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption=referral_text,
            reply_markup=inline_keyboard,
            parse_mode='HTML'
        )
    else:
        await bot.send_message(callback_query.from_user.id, "Пользователь не найден в базе данных.")

async def process_promo_code(message: types.Message, state: FSMContext):
    promo_code = message.text

    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT * FROM users WHERE promo=? AND id!=?", (promo_code, user_id))
            other_user_data = await cursor.fetchone()

            if other_user_data:
                await cursor.execute("UPDATE users SET valid_promo = 0 WHERE id = ?", (user_id,))

                await cursor.execute("UPDATE users SET quantity_referals = quantity_referals + 1 WHERE promo = ?",
                                     (promo_code,))
                await db.commit()
                await message.reply("Промокод активирован")

                async with aiosqlite.connect('database.db') as db:
                    await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, None))
                    await db.commit()

            elif promo_code == user_data[8]:
                await message.reply("Это ваш собственный промокод")

                async with aiosqlite.connect('database.db') as db:
                    await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, None))
                    await db.commit()
            else:
                await message.reply("Неверный промокод")
                async with aiosqlite.connect('database.db') as db:
                    await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, None))
                    await db.commit()
    await main_panel(message)
    await state.finish()

async def back_to_main_panel(callback_query: types.CallbackQuery):
    await callback_query.answer()
    inline_keyboard = get_inline_keyboard()
    with open('images/image.jpg', 'rb') as photo:
        await bot.edit_message_media(
            media=types.InputMediaPhoto(media=photo),
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=inline_keyboard
        )

async def show_user_publications(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id

    current_publication = await state.get_data()
    current_publication = current_publication.get('current_publication', 1)

    async with aiosqlite.connect('database.db') as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT COUNT(*) FROM publication WHERE user_id=?", (user_id,))
        quantity_media = await cursor.fetchone()

    if quantity_media:
        quantity_media = quantity_media[0]

        async with aiosqlite.connect('database.db') as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT * FROM publication WHERE user_id=? ORDER BY num_user_publ ASC LIMIT 1 OFFSET ?", (user_id, current_publication - 1))
            user_publication = await cursor.fetchone()

        if user_publication:
            publ_file_id = user_publication[2]
            description = user_publication[3]
            publication_data = f"\n❤️Лайки: {user_publication[4]}\n👁Просмотры: {user_publication[5]}"

            async with aiosqlite.connect('database.db') as db:
                cursor = await db.cursor()
                await cursor.execute("SELECT COUNT(*) FROM publication WHERE num_user_publ=?", (user_publication[11],))
                parts_count = await cursor.fetchone()
            parts_count = parts_count[0]

            async with aiosqlite.connect('database.db') as db:
                cursor = await db.cursor()
                await cursor.execute("SELECT COUNT(*) FROM publication WHERE num_user_publ=? AND user_id=? AND id<=?", (user_publication[11], user_id, user_publication[0]))
                current_part_number = await cursor.fetchone()
            current_part_number = current_part_number[0]

            if description:
                full_description = f"{description}\n{publication_data}"
                if parts_count > 1:
                    full_description += f"\n (Часть {current_part_number}/{parts_count})"
            else:
                full_description = publication_data

            inline_keyboard = InlineKeyboardMarkup().row(
                InlineKeyboardButton("⬅️", callback_data="previous_publication"),
                InlineKeyboardButton(f"{current_publication}/{quantity_media}", callback_data="current_publication"),
                InlineKeyboardButton("➡️", callback_data="next_publication")
            ).add(
                InlineKeyboardButton("Удалить медиафайл", callback_data="delete_publication")
            ).add(
                InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
            )

            media_type = types.InputMediaPhoto

            if user_publication[9] == 'animation':
                media_type = types.InputMediaAnimation
            elif user_publication[9] == 'video':
                media_type = types.InputMediaVideo

            await bot.edit_message_media(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                media=media_type(media=publ_file_id, caption=full_description),
                reply_markup=inline_keyboard
            )
        else:
            await bot.send_message(callback_query.from_user.id, "У вас пока нет публикаций.")

            await state.set_data({'current_publication': current_publication})
    else:
        await bot.send_message(callback_query.from_user.id, "У вас пока нет медиа.")

async def delete_publication(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    current_publication = await state.get_data()
    current_publication = current_publication.get('current_publication', 1)

    async with aiosqlite.connect('database.db') as db:
        async with db.cursor() as cursor:

            await cursor.execute("SELECT * FROM publication WHERE user_id=? ORDER BY num_user_publ ASC LIMIT 1 OFFSET ?", (user_id, current_publication - 1))
            user_publication = await cursor.fetchone()

            if user_publication:
                publ_id = user_publication[0]
                kod = user_publication[8]

                await cursor.execute("SELECT COUNT(*) FROM publication WHERE kod=? AND id<>?", (kod, publ_id))
                other_publications_count = await cursor.fetchone()
                other_publications_count = other_publications_count[0]

                await cursor.execute("DELETE FROM publication WHERE id=?", (publ_id,))
                await db.commit()

                if other_publications_count > 0:
                    await cursor.execute("UPDATE users SET quantity_media = quantity_media - 1 WHERE id=?", (user_id,))
                else:
                    await cursor.execute("UPDATE users SET quantity_publication = quantity_publication - 1, quantity_media = quantity_media - 1 WHERE id=?", (user_id,))
                await db.commit()

                await cursor.execute("SELECT COUNT(*) FROM publication WHERE user_id=?", (user_id,))
                remaining_publications = await cursor.fetchone()
                remaining_publications = remaining_publications[0]

                if remaining_publications > 0:
                    await state.set_data({'current_publication': 1})
                else:
                    await bot.send_message(user_id, "У вас закончились публикации")
                    await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
                    return

                await show_user_publications(callback_query, state)
            else:
                await bot.send_message(user_id, "У вас закончились публикации")

async def switch_publication_page(callback_query: types.CallbackQuery, state: FSMContext, direction: str):
    await callback_query.answer()
    user_id = callback_query.from_user.id

    current_publication = await state.get_data()
    current_publication = current_publication.get('current_publication', 1)

    async with aiosqlite.connect('database.db') as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT COUNT(*) FROM publication WHERE user_id=?", (user_id,))
        quantity_media = await cursor.fetchone()

        if quantity_media:
            quantity_media = quantity_media[0]

            if quantity_media == 1:
                pass
                return

            if current_publication < 1:
                current_publication = 1
            elif current_publication > quantity_media:
                current_publication = quantity_media

            if direction == "next":
                if current_publication == quantity_media:
                    current_publication = 1
                else:
                    current_publication += 1
            elif direction == "previous":
                if current_publication == 1:
                    current_publication = quantity_media
                else:
                    current_publication -= 1

            await state.set_data({'current_publication': current_publication})
            await show_user_publications(callback_query, state)
        else:
            await bot.send_message(callback_query.from_user.id, "У вас пока нет медиа.")


async def previous_publication_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await switch_publication_page(callback_query, state, "previous")

async def next_publication_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await switch_publication_page(callback_query, state, "next")

async def show_user_profile(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        is_subscribed = await get_subscription_status(user_id)
        subscription_status = "активен⚡️" if is_subscribed else "не активен💔(подпишитесь на канал проекта чтобы получить буст)"

        await update_subscription_status(user_id, is_subscribed)

        profile_text = f"<b>🍏 Kоличество публикаций:</b> {user_data[3]} 🌐\n" \
                       f"<b>🍇 Kоличество медиа:</b> {user_data[4]} 🌐\n" \
                       f"{'➖' * 15}\n" \
                       f"<b>🍉 Kоличество лайков:</b> {user_data[5]} ❤️\n" \
                       f"<b>🍒 Kоличество просмотров:</b> {user_data[6]} 👀\n" \
                       f"{'➖' * 15}\n" \
                       f"<b>🍑 Промокод:</b> <code>{user_data[8]}</code> 💳\n" \
                       f"<b>🍍 Количество рефералов:</b> {user_data[10]} 👫\n" \
                       f"<b>🍌 Буст:</b> {subscription_status}\n"

        inline_keyboard = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
        )


        await bot.edit_message_caption(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            caption=profile_text,
            reply_markup=inline_keyboard,
            parse_mode='HTML'
        )
    else:
        await bot.send_message(callback_query.from_user.id, "Пользователь не найден в базе данных.")

async def show_rating(callback_query: types.CallbackQuery, state: FSMContext):
    user_count = await get_user_count()

    if user_count < 1000:
        await callback_query.answer(
            text="Рейтинг появится при достижении 10,000 пользователей.",
            show_alert=False
        )
        return

    top_users = await get_top_5_users_with_most_likes()

    if top_users:
        user_id = callback_query.from_user.id

        user_rank = None
        for rank, (uid, _, _) in enumerate(top_users, start=1):
            if uid == user_id:
                user_rank = rank
                break

        rating_text = "<b>Топ 5 самых известных пользователей:</b>\n\n"
        emojis = ["🤴", "👸", "🤵", "👰", "🧑‍💼"]
        for rank, (uid, username, quantity_like) in enumerate(top_users[:5], start=1):
            if not username:
                username = "имя не указано :("
            rating_text += f"{emojis[rank-1]} <b>Место {rank}:</b> @{username}\n"

        if user_rank is not None and user_rank <= 5:
            rating_text += f"\n➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖\n<b>Ваше место в рейтинге :</b> <b>{user_rank}</b>"

    else:
        rating_text = "Не удалось получить топ-5 пользователей."

    inline_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Назад", callback_data="back_to_main_panel")
    )

    await bot.edit_message_caption(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        caption=rating_text,
        reply_markup=inline_keyboard,
        parse_mode='HTML'
    )

def register_handlers_mainpanel(dp):
    dp.register_message_handler(main_panel, text='📁 Меню 📋')
    dp.register_callback_query_handler(show_user_profile, lambda c: c.data == 'button_1')
    dp.register_callback_query_handler(handle_news_button, lambda c: c.data == 'button_2')
    dp.register_callback_query_handler(show_rating, lambda c: c.data == 'button_3')
    dp.register_callback_query_handler(back_to_main_panel, lambda c: c.data == 'back_to_main_panel')
    dp.register_callback_query_handler(show_user_publications, lambda c: c.data == 'button_4')
    dp.register_callback_query_handler(next_publication_callback, lambda c: c.data == 'next_publication')
    dp.register_callback_query_handler(previous_publication_callback, lambda c: c.data == 'previous_publication')
    dp.register_callback_query_handler(show_referral_program, lambda c: c.data == 'button_5', state="*")
    dp.register_callback_query_handler(process_input_promo_code, lambda c: c.data == 'input_promo_code', state="*")
    dp.register_message_handler(process_promo_code, state="waiting_for_promo_code")
    dp.register_callback_query_handler(delete_publication, lambda c: c.data == 'delete_publication')