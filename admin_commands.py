import aiosqlite
from aiogram.dispatcher import FSMContext
from config import admin_id
from keyboards import get_menu_keyboard
from aiogram import types
from aiogram.dispatcher.filters.state import StatesGroup, State
from config import bot
import datetime
from config import DATABASE

class NewsState(StatesGroup):
    waiting_for_news_text = State()

class BanState(StatesGroup):
    waiting_for_user_id = State()
class UnbanState(StatesGroup):
    waiting_for_user_id = State()

class PublicationState(StatesGroup):
    CompPublications = State()

class DeletePublicationState(StatesGroup):
    waiting_for_kod = State()

class ShowUserState(StatesGroup):
    waiting_for_user_id = State()


class DeleteAllPublicationsState(StatesGroup):
    waiting_for_user_id = State()

class AddUserToAdvertiserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_quantity_publications = State()
    waiting_for_link = State()
    waiting_for_button_name = State()

async def add_user_to_advertiser(message: types.Message):
    if message.from_user.id not in admin_id:
        return
    await message.answer("Пожалуйста, отправьте ID пользователя:")
    await AddUserToAdvertiserState.waiting_for_user_id.set()

async def process_user_id_for_advertiser(message: types.Message, state: FSMContext):
    if message.from_user.id not in admin_id:
        return
    async with state.proxy() as data:
        user_id = message.text.strip()
        data['user_id'] = user_id
    await message.answer(f"Отлично! Теперь отправьте количество публикаций для пользователя с ID {user_id}:")
    await AddUserToAdvertiserState.waiting_for_quantity_publications.set()

async def process_quantity_publications(message: types.Message, state: FSMContext):
    if message.from_user.id not in admin_id:
        return
    async with state.proxy() as data:
        quantity_publications = message.text.strip()
        data['quantity_publications'] = quantity_publications
    await message.answer("Теперь отправьте ссылку для пользователя:")
    await AddUserToAdvertiserState.waiting_for_link.set()

async def process_link(message: types.Message, state: FSMContext):
    if message.from_user.id not in admin_id:
        return
    async with state.proxy() as data:
        link = message.text.strip()
        data['link'] = link
    await message.answer("Теперь отправьте название кнопки для пользователя:")
    await AddUserToAdvertiserState.waiting_for_button_name.set()

async def process_button_name(message: types.Message, state: FSMContext):
    if message.from_user.id not in admin_id:
        return
    async with state.proxy() as data:
        user_id = data['user_id']
        quantity_publications = data['quantity_publications']
        link = data['link']
        button_name = message.text.strip()
        await add_user_to_advertiser_in_db(user_id, quantity_publications, link, button_name)
        await message.answer(f"Пользователь с ID {user_id} успешно добавлен в таблицу 'advertiser' с количеством публикаций {quantity_publications}, ссылкой {link} и названием кнопки {button_name}!")
    await state.finish()

async def add_user_to_advertiser_in_db(user_id, quantity_publications, link, button_name):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT INTO advertiser (id, quantity_publ, link, button_name) VALUES (?, ?, ?, ?)",
                         (user_id, quantity_publications, link, button_name))
        await db.commit()
async def news_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.reply("Введите текст для новости:")
        await NewsState.waiting_for_news_text.set()

async def process_news_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['user_id'] = message.from_user.id
        data['news_text'] = message.text
    await update_news_in_db(data['user_id'], data['news_text'])
    await message.reply("Текст новости обновлен.")
    await state.finish()
async def update_news_in_db(user_id: int, news_text: str):
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute("""
            INSERT INTO news (user_id, last_news) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_news = excluded.last_news;
        """, (user_id, news_text))
        await conn.commit()

async def show_publication_with_complaint(message: types.Message, state: FSMContext):
    async with aiosqlite.connect('database.db') as db:
        await PublicationState.CompPublications.set()
        cursor = await db.execute(
            'SELECT id, kod, publ_file_id, descriptions, complaint, media_type FROM publication WHERE complaint != ? ORDER BY RANDOM() LIMIT 1',
            ('9',))
        complaint_publication = await cursor.fetchone()

        if complaint_publication:
            publication_id, kod, publ_file_id, description, complaint_reason, media_type = complaint_publication
            await state.update_data(current_publication_id=publication_id, current_publication_kod=kod)

            keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            keyboard_markup.add(
                types.KeyboardButton(f"Убрать жалобу"),
                types.KeyboardButton("Удалить публикацию"),
                types.KeyboardButton("В меню")
            )

            await bot.send_message(message.chat.id, "💃", reply_markup=keyboard_markup)

            if media_type == 'video':
                await bot.send_video(message.chat.id, video=publ_file_id, caption=f"{description}\n\nПричина жалобы: {complaint_reason}")
            elif media_type == 'animation':
                await bot.send_animation(message.chat.id, animation=publ_file_id, caption=f"\n\nПричина жалобы: {complaint_reason}")
            else:
                cursor = await db.execute('SELECT publ_file_id FROM publication WHERE kod = ?', (kod,))
                photos = await cursor.fetchall()
                photo_ids = [types.InputMediaPhoto(photo[0], caption=f"{description}\n\nПричина жалобы: {complaint_reason}" if i == 0 else None) for
                             i, photo in enumerate(photos)]
                await bot.send_media_group(message.chat.id, photo_ids)
        else:
            await message.bot.send_message(message.chat.id, "Больше публикаций с жалобами нет.",
                                           reply_markup=get_menu_keyboard(is_admin=True))
            await state.reset_state()


async def remove_complaint(message: types.Message, state: FSMContext):
    data = await state.get_data()
    publication_id = data.get('current_publication_id')
    publication_kod = data.get('current_publication_kod')

    if publication_id and publication_kod:
        async with aiosqlite.connect('database.db') as db:

            await db.execute('UPDATE publication SET complaint = ? WHERE id = ?', ('9', publication_id))
            await db.commit()

            await db.execute('UPDATE publication SET complaint = ? WHERE kod = ?', ('9', publication_kod))
            await db.commit()

            await message.reply("Жалоба успешно убрана.")

            await show_publication_with_complaint(message, state)
    else:
        await message.reply("Ошибка: Не удалось определить идентификатор или код публикации.")


async def remove_publication(message: types.Message, state: FSMContext):
    data = await state.get_data()
    publication_id = data.get('current_publication_id')
    publication_kod = data.get('current_publication_kod')

    if publication_id and publication_kod:
        async with aiosqlite.connect('database.db') as db:

            quantity_media_deleted = 0

            cursor = await db.execute('SELECT COUNT(*) FROM publication WHERE id = ?', (publication_id,))
            result = await cursor.fetchone()
            if result and result[0] > 0:
                quantity_media_deleted += result[0]

                await db.execute('DELETE FROM publication WHERE id = ?', (publication_id,))
                await db.commit()

            cursor = await db.execute('SELECT id FROM publication WHERE kod = ? AND id != ?',
                                      (publication_kod, publication_id))
            similar_publications = await cursor.fetchall()
            for pub_id in similar_publications:
                await db.execute('DELETE FROM publication WHERE id = ?', (pub_id[0],))
                await db.commit()

                quantity_media_deleted += 1

            await db.execute('UPDATE users SET quantity_publication = quantity_publication - 1 WHERE id = ?',
                             (message.from_user.id,))
            await db.execute('UPDATE users SET quantity_media = quantity_media - ? WHERE id = ?',
                             (quantity_media_deleted, message.from_user.id))
            await db.commit()

            await message.reply("Публикация успешно удалена.")

            await show_publication_with_complaint(message, state)
    else:
        await message.reply("Ошибка: Не удалось определить идентификатор или код публикации.")

async def menu_button(message: types.Message, state: FSMContext):
    await state.reset_state()
    is_admin = message.from_user.id in admin_id
    keyboard_markup = get_menu_keyboard(is_admin)
    await bot.send_message(message.chat.id, "🔮", reply_markup=keyboard_markup)

async def get_users_stats():
    async with aiosqlite.connect(DATABASE) as db:

        total_users_query = await db.execute("SELECT COUNT(id) FROM users")
        total_users = await total_users_query.fetchone()

        today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_users_query = await db.execute("SELECT COUNT(id) FROM users WHERE data_time LIKE ?", (f"{today}%",))
        today_users = await today_users_query.fetchone()

        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_users_query = await db.execute("SELECT COUNT(id) FROM users WHERE data_time LIKE ?", (f"{yesterday}%",))
        yesterday_users = await yesterday_users_query.fetchone()

        week_start = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        week_users_query = await db.execute("SELECT COUNT(id) FROM users WHERE data_time >= ?", (week_start,))
        week_users = await week_users_query.fetchone()

        month_start = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        month_users_query = await db.execute("SELECT COUNT(id) FROM users WHERE data_time >= ?", (month_start,))
        month_users = await month_users_query.fetchone()

    stats_text = (
        f"👤 Всего пользователей: {total_users[0]}\n"
        f"👤 Пользователей за день: {today_users[0]}\n"
        f"👤 Пользователей за вчера: {yesterday_users[0]}\n"
        f"👤 Пользователей за неделю: {week_users[0]}\n"
        f"👤 Пользователей за месяц: {month_users[0]}"
    )

    return stats_text


async def stats_command(message: types.Message):
    stats = await get_users_stats()
    await message.reply(stats)

async def ban_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.reply("Введите ID пользователя для бана:")
        await BanState.waiting_for_user_id.set()

async def process_user_id_for_ban(message: types.Message, state: FSMContext):
    user_id_to_ban = message.text
    await ban_user_in_db(user_id_to_ban)
    await message.reply(f"Пользователь с ID {user_id_to_ban} забанен.")
    await state.finish()

async def ban_user_in_db(user_id: int):
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute("UPDATE users SET banned = 1 WHERE id = ?", (user_id,))
        await conn.commit()

async def unban_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.reply("Введите ID пользователя для разбана:")
        await UnbanState.waiting_for_user_id.set()

async def process_user_id_for_unban(message: types.Message, state: FSMContext):
    user_id_to_unban = message.text
    await unban_user_in_db(user_id_to_unban)
    await message.reply(f"Пользователь с ID {user_id_to_unban} разбанен.")
    await state.finish()

async def unban_user_in_db(user_id: int):
    async with aiosqlite.connect(DATABASE) as conn:
        await conn.execute("UPDATE users SET banned = 0 WHERE id = ?", (user_id,))
        await conn.commit()

async def help_command(message: types.Message):
    if message.from_user.id in admin_id:
        commands = [
            "/stats - Показать статистику",
            "/news - Добавить новость",
            "/com - Показать публикацию с жалобой",
            "/ban - Забанить пользователя",
            "/unban - Разбанить пользователя",
            "/adver - Добавить пользователя к рекламодателям",
            "/del - Удалить публикацию по коду",
            "/delall - Удалить все публикации пользователя"
            "/show - показать 10 публикаций пользователя "
        ]
        await message.answer("\n".join(commands))
async def show_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.answer("Введите ID пользователя:")
        await ShowUserState.waiting_for_user_id.set()

async def process_user_id_for_show_publ(message: types.Message, state: FSMContext):
    user_id = message.text

    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                await message.answer("Пользователь с таким ID существует. Отправляю 10 последних публикаций.")
                async with db.execute("SELECT * FROM publication WHERE user_id = ? ORDER BY datetime DESC LIMIT 10",
                                      (user_id,)) as pub_cursor:
                    publications = await pub_cursor.fetchall()
                    if publications:
                        for pub in publications:
                            publ_file_id = pub[2]
                            descriptions = pub[3]
                            kod = pub[8]
                            media_type = pub[9]
                            if media_type == 'photo':
                                await bot.send_photo(message.chat.id, publ_file_id, caption=descriptions)
                            elif media_type == 'video':
                                await bot.send_video(message.chat.id, publ_file_id, caption=descriptions)
                            elif media_type == 'animation':
                                await bot.send_animation(message.chat.id, publ_file_id, caption=descriptions)
                            else:
                                await bot.send_message(message.chat.id, f"Неизвестный тип медиа: {media_type}")

                            await bot.send_message(message.chat.id, f"Код публикации: {kod}")
                    else:
                        await message.answer("У пользователя нет публикаций.")
            else:
                await message.answer("Пользователь с таким ID не найден.")

    await state.finish()


async def del_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.answer("Введите код публикации, которую хотите удалить:")
        await DeletePublicationState.waiting_for_kod.set()


async def process_kod_for_del(message: types.Message, state: FSMContext):
    kod = message.text
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT user_id, COUNT(*) FROM publication WHERE kod = ? GROUP BY user_id",
                              (kod,)) as cursor:
            result = await cursor.fetchone()
            if result:
                user_id, count = result
                await message.answer(f"Найдено {count} публикаций с таким кодом. Удаляю...")

                await db.execute("DELETE FROM publication WHERE kod = ?", (kod,))
                await db.commit()

                await db.execute(
                    "UPDATE users SET quantity_publication = quantity_publication - 1, quantity_media = quantity_media - ? WHERE id = ?",
                    (count, user_id))
                await db.commit()

                await message.answer(f"Успешно удалено {count} публикаций. Обновлена информация о пользователе.")
            else:
                await message.answer("Публикация с таким кодом не найдена.")
    await state.finish()


async def delall_command(message: types.Message):
    if message.from_user.id in admin_id:
        await message.answer("Введите ID пользователя, все публикации которого хотите удалить:")
        await DeleteAllPublicationsState.waiting_for_user_id.set()


async def process_user_id_for_delall(message: types.Message, state: FSMContext):
    user_id = int(message.text)
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT id FROM users WHERE id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if user:
                async with db.execute("SELECT COUNT(*) FROM publication WHERE user_id = ?", (user_id,)) as count_cursor:
                    count = await count_cursor.fetchone()
                    await db.execute("DELETE FROM publication WHERE user_id = ?", (user_id,))
                    await db.execute("UPDATE users SET quantity_publication = 0, quantity_media = 0 WHERE id = ?", (user_id,))
                    await db.commit()
                    await message.answer(f"Успешно удалено {count[0]} публикаций пользователя")
            else:
                await message.answer("Пользователь с таким ID не найден.")
    await state.finish()
def register_handlers_admin_functions(dp):
    dp.register_message_handler(stats_command, commands=['stats'], state='*')
    dp.register_message_handler(news_command, commands=['news'])
    dp.register_message_handler(process_news_text, state=NewsState.waiting_for_news_text)
    dp.register_message_handler(show_publication_with_complaint, commands=['com'])
    dp.register_message_handler(remove_complaint, text="Убрать жалобу", state=PublicationState.CompPublications)
    dp.register_message_handler(remove_publication, text="Удалить публикацию", state=PublicationState.CompPublications)
    dp.register_message_handler(menu_button, text="В меню", state='*')
    dp.register_message_handler(ban_command, commands=['ban'])
    dp.register_message_handler(process_user_id_for_ban, state=BanState.waiting_for_user_id)
    dp.register_message_handler(unban_command, commands=['unban'])
    dp.register_message_handler(process_user_id_for_unban, state=UnbanState.waiting_for_user_id)
    dp.register_message_handler(add_user_to_advertiser, commands="adver", state="*")
    dp.register_message_handler(process_user_id_for_advertiser, state=AddUserToAdvertiserState.waiting_for_user_id)
    dp.register_message_handler(process_quantity_publications,
                                state=AddUserToAdvertiserState.waiting_for_quantity_publications)
    dp.register_message_handler(process_link, state=AddUserToAdvertiserState.waiting_for_link)
    dp.register_message_handler(process_button_name, state=AddUserToAdvertiserState.waiting_for_button_name)

    dp.register_message_handler(help_command, commands=['help'])
    dp.register_message_handler(show_command, commands=['show'])
    dp.register_message_handler(process_user_id_for_show_publ, state=ShowUserState.waiting_for_user_id)
    dp.register_message_handler(del_command, commands=['del'], state='*')
    dp.register_message_handler(process_kod_for_del, state=DeletePublicationState.waiting_for_kod)
    dp.register_message_handler(delall_command, commands=['delall'], state='*')
    dp.register_message_handler(process_user_id_for_delall, state=DeleteAllPublicationsState.waiting_for_user_id)
