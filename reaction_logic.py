from aiogram import types
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext
from view_publ import PublicationState, send_next_publication, send_media_with_description
import aiosqlite
from config import bot
from keyboards import menu_command
from keyboards import get_reaction_keyboard
from database import get_user_state


async def handle_reaction(message: types.Message, state: FSMContext):
    emoji = message.text
    if await state.get_state() == PublicationState.ViewingPublications.state:
        data = await state.get_data()
        current_publication_id = data.get('current_publication_id')
        if current_publication_id is not None:
            if emoji == "❤️":
                await like_publication(message, state)
            elif emoji == "💤":
                await state.finish()
                await menu_command(message)

                async with aiosqlite.connect('database.db') as db:
                    await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                                     (message.from_user.id, None))
                    await db.commit()
            elif emoji == "👎":
                await dislike_publication(message, state)
        else:
            await message.reply("Произошла ошибка, попробуйте снова.")
            await menu_command(message)
            await state.finish()
        return

    user_state = await get_user_state(message.from_user.id)
    if user_state == "showing_publication":
        if emoji == "❤️":
            await send_media_with_description(message, state)
        elif emoji == "👎":
            await send_media_with_description(message, state)
        elif emoji == "💤":
            await menu_command(message)
            async with aiosqlite.connect('database.db') as db:
                await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                                 (message.from_user.id, None))
                await db.commit()


async def update_publication_popularity(db, kod, user_id):
    async with db.execute('SELECT likes, views FROM publication WHERE kod = ?', (kod,)) as cursor:
        publication_row = await cursor.fetchone()

    if publication_row:
        likes, views = publication_row

        async with db.execute('SELECT subscrib_chnl, quantity_referals FROM users WHERE id = ?', (user_id,)) as user_cursor:
            user_row = await user_cursor.fetchone()

        if user_row:
            subscrib_chnl, quantity_referals = user_row

            if views == 0:
                popularity = 100
            else:
                if quantity_referals >= 5 and subscrib_chnl:
                    multiplier = 1300
                elif quantity_referals >= 3:
                    multiplier = 1200
                elif quantity_referals >= 1 or subscrib_chnl:
                    multiplier = 1100
                else:
                    multiplier = 1000

                popularity = ((likes + 1) / (views + 1)) * multiplier

            await db.execute('UPDATE publication SET popularity = ? WHERE kod = ?', (popularity, kod))
            await db.commit()

async def like_publication(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_publication_id = data.get('current_publication_id')
    liker_id = message.from_user.id

    if current_publication_id is not None:
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('SELECT kod, user_id, theme_media FROM publication WHERE id = ?', (current_publication_id,)) as cursor:
                result = await cursor.fetchone()

            if result:
                kod, user_id, theme_media = result

                await db.execute('UPDATE publication SET likes = likes + 1, views = views + 1 WHERE kod = ?', (kod,))

                await db.execute(
                    'UPDATE users SET quantity_like = quantity_like + 1, quantity_views = quantity_views + 1 WHERE id = ?',
                    (user_id,)
                )

                await db.execute(
                    'UPDATE users SET quantity_views_eng = quantity_views_eng + 1 WHERE id = ?',
                    (liker_id,)
                )

                if theme_media in ['Эст', 'Муз', 'Машины']:
                    await db.execute('UPDATE users SET aesthetics = aesthetics + 1 WHERE id = ?', (liker_id,))
                elif theme_media in ['Малол', 'Празд', 'Юмор', 'Кринж', 'Жиза']:
                    await db.execute('UPDATE users SET humor = humor + 1 WHERE id = ?', (liker_id,))
                elif theme_media == 'Спорт':
                    await db.execute('UPDATE users SET sport = sport + 1 WHERE id = ?', (liker_id,))
                elif theme_media == 'хуйня':
                    pass

                await update_publication_popularity(db, kod, user_id)

                async with db.execute('SELECT quantity_views_eng, humor, aesthetics, sport FROM users WHERE id = ?', (liker_id,)) as cursor:
                    user_stats = await cursor.fetchone()

                if user_stats:
                    quantity_views_eng, humor, aesthetics, sport = user_stats

                    if quantity_views_eng >= 25:
                        favorite_theme = 'random'
                        narrow_theme = theme_media

                        if quantity_views_eng >= 40:
                            humor, aesthetics, sport, quantity_views_eng = 0, 0, 0, 0
                            narrow_theme = None
                        else:
                            if humor >= aesthetics and humor >= sport:
                                favorite_theme = 'humor'
                            elif aesthetics >= humor and aesthetics >= sport:
                                favorite_theme = 'aesthetics'
                            elif sport >= humor and sport >= aesthetics:
                                favorite_theme = 'sport'

                        await db.execute(
                            'UPDATE users SET favorite_theme = ?, narrow_theme = ?, humor = ?, aesthetics = ?, sport = ?, quantity_views_eng = ? WHERE id = ?',
                            (favorite_theme, narrow_theme, humor, aesthetics, sport, quantity_views_eng, liker_id)
                        )

                await db.commit()

    await send_next_publication(message, state)

async def dislike_publication(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_publication_id = data.get('current_publication_id')
    disliker_id = message.from_user.id

    if current_publication_id is not None:
        async with aiosqlite.connect('database.db') as db:
            async with db.execute('SELECT kod, user_id FROM publication WHERE id = ?', (current_publication_id,)) as cursor:
                result = await cursor.fetchone()

            if result:
                kod, user_id = result

                await db.execute('UPDATE publication SET views = views + 1 WHERE kod = ?', (kod,))

                await db.execute(
                    'UPDATE users SET quantity_views = quantity_views + 1 WHERE id = ?',
                    (user_id,)
                )

                await db.execute(
                    'UPDATE users SET quantity_views_eng = quantity_views_eng + 1 WHERE id = ?',
                    (disliker_id,)
                )

                await update_publication_popularity(db, kod, user_id)

                await db.execute(
                    'UPDATE users SET narrow_theme = NULL WHERE id = ?',
                    (disliker_id,)
                )

                await db.commit()
    await send_next_publication(message, state)


async def handle_complaint(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with aiosqlite.connect('database.db') as db:
        cursor = await db.execute('SELECT state FROM use_state WHERE id = ?', (user_id,))
        row = await cursor.fetchone()

        if not row or row[0] != 'showing_publication':
            return

        if row[0] == 'showing_publication':
            current_state = await state.get_state()
            if current_state != PublicationState.ViewingPublications.state:
                await bot.send_message(message.chat.id, "Бот был перезапущен, не удалось пожаловаться на публикацию:(")
                await send_next_publication(message, state)
                await PublicationState.ViewingPublications.set()
                return

    complaint_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    buttons = ["1. 🛑", "2. 💉", "3. 🚫", "4. 💼", "5. 🤖", "9"]
    complaint_keyboard.row(*buttons)
    await bot.send_message(message.chat.id, "Выберите тип жалобы:\n\n"
                                            "1. 🛑 Неприемлемый контент.\n"
                                            "2. 💉 Нарушение правил по наркотикам.\n"
                                            "3. 🚫 Спам или нежелательная рассылка.\n"
                                            "4. 💼 Продажа товаров и реклама.\n"
                                            "5. 🤖 Другое.\n"
                                            "***\n"
                                            "9. Вернуться назад.", reply_markup=complaint_keyboard)
    await PublicationState.ViewingPublications.set()

    async with aiosqlite.connect('database.db') as db:
        await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (user_id, 'waiting_reason'))
        await db.commit()
async def handle_complaint_reason(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    reason = message.text.split(". ", 1)[1] if ". " in message.text else message.text
    data = await state.get_data()
    current_publication_id = data.get('current_publication_id')
    user_id = message.from_user.id

    if current_state == PublicationState.ViewingPublications.state and current_publication_id:
        async with aiosqlite.connect('database.db') as db:
            await db.execute("UPDATE publication SET complaint = ? WHERE id = ?", (reason, current_publication_id))
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                             (user_id, 'showing_publication'))
            await db.commit()

        await message.reply("Ваша жалоба зарегистрирована. Спасибо за ваше сообщение.",
                            reply_markup=get_reaction_keyboard())
        await PublicationState.ViewingPublications.set()
        await send_next_publication(message, state)
    else:
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT state FROM use_state WHERE id = ?", (user_id,))
            user_state = await cursor.fetchone()

        if user_state and user_state[0] == 'waiting_reason':
            await message.reply("Ваша жалоба зарегистрирована. Спасибо за ваше сообщение.",
                                reply_markup=get_reaction_keyboard())
            await PublicationState.ViewingPublications.set()
            await send_next_publication(message, state)

            async with aiosqlite.connect('database.db') as db:
                await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                                 (user_id, 'showing_publication'))
                await db.commit()

async def handle_complaint_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()

    if current_state == PublicationState.ViewingPublications.state:
        await message.reply("Жалоба отменена.", reply_markup=get_reaction_keyboard())

        async with aiosqlite.connect('database.db') as db:
            await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)', (message.from_user.id, 'showing_publication'))
            await db.commit()

        await PublicationState.ViewingPublications.set()
        await send_next_publication(message, state)
    else:
        async with aiosqlite.connect('database.db') as db:
            cursor = await db.execute("SELECT state FROM use_state WHERE id = ?", (message.from_user.id,))
            user_state = await cursor.fetchone()

        if user_state and user_state[0] == 'waiting_reason':
            await message.reply("Жалоба отменена.", reply_markup=get_reaction_keyboard())
            await PublicationState.ViewingPublications.set()
            await send_next_publication(message, state)

            async with aiosqlite.connect('database.db') as db:
                await db.execute('INSERT OR REPLACE INTO use_state (id, state) VALUES (?, ?)',
                                 (message.from_user.id, 'showing_publication'))
                await db.commit()
        else:
            pass

def register_reaction_handlers(dp):
    dp.register_message_handler(handle_complaint, Text(equals="жалоба"), state="*")
    dp.register_message_handler(handle_reaction, lambda message: message.text in ["❤️", "👎" ,"💤"], state="*")
    dp.register_message_handler(handle_complaint_reason, lambda message: message.text in ["1. 🛑", "2. 💉", "3. 🚫", "4. 💼", "5. 🤖"], state="*")
    dp.register_message_handler(handle_complaint_cancel, Text(equals="9"), state="*")
