import random
import string
from datetime import datetime
from config import DATABASE
from aiogram.types import ChatMemberStatus
import aiosqlite
from config import bot, CHANNEL_ID

async def create_connection(db_file):
    try:
        conn = await aiosqlite.connect(db_file)
        return conn
    except aiosqlite.Error as e:
        print(e)
    return None

async def create_tables(conn):
    create_tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            data_time TEXT NOT NULL,
            quantity_publication INTEGER DEFAULT 0,
            quantity_media INTEGER DEFAULT 0,
            quantity_like INTEGER DEFAULT 0,
            quantity_views INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0,
            promo TEXT,
            valid_promo INTEGER DEFAULT 1,
            quantity_referals INTEGER DEFAULT 0,
            subscrib_chnl TEXT,
            favorite_theme TEXT DEFAULT 'random',
            narrow_theme TEXT,
            quantity_views_eng INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            publ_file_id TEXT,
            descriptions TEXT,
            likes INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0,
            datetime TEXT,
            complaint TEXT DEFAULT 9,
            kod TEXT,
            media_type TEXT,
            popularity INTEGER DEFAULT 50,
            num_user_publ INTEGER DEFAULT 0,
            theme_media TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS news (
            user_id INTEGER PRIMARY KEY,
            last_news TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS use_state (
            id INTEGER PRIMARY KEY,
            state INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS advertiser(
            id INTEGER PRIMARY KEY,
            link TEXT,
            button_name TEXT,
            quantity_publ INTEGER,
            value TEXT
        )
        """

    ]
    try:
        for sql_query in create_tables_sql:
            await conn.execute(sql_query)
    except aiosqlite.Error as e:
        print("Error occurred while creating tables:", e)
        import traceback
        traceback.print_exc()

async def add_column_if_not_exists(conn, table_name, column_name, column_definition):
    try:
        await conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
    except aiosqlite.Error as e:
        if 'duplicate column name' not in str(e):
            print(e)

def generate_promo_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

async def add_user(conn, user_id, username):
    promo_code = generate_promo_code()
    sql = ''' INSERT INTO users(id, username, data_time, promo) VALUES(?,?,?,?) '''
    cur = await conn.execute(sql, (user_id, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), promo_code))
    await conn.commit()
    return cur.lastrowid

async def user_exists(conn, user_id):
    cur = await conn.execute("SELECT id FROM users WHERE id=?", (user_id,))
    return await cur.fetchone() is not None


async def get_user_data(user_id):
    async with aiosqlite.connect('database.db') as db:
        cursor = await db.cursor()
        await cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user_data = await cursor.fetchone()
    return user_data
async def get_latest_news_from_db():
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT last_news FROM news ORDER BY rowid DESC LIMIT 1') as cursor:
            row = await cursor.fetchone()
            if row:
                latest_news = row[0]
            else:
                latest_news = "Пока что новостей нет."
    return latest_news

async def get_top_5_users_with_most_likes():
    async with aiosqlite.connect('database.db') as conn:
        cursor = await conn.execute('''SELECT id, username, quantity_like
                                      FROM users
                                      ORDER BY quantity_like DESC
                                      LIMIT 5''')
        top_users = await cursor.fetchall()
    return top_users

async def get_subscrib_chnl_from_db(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        query = "SELECT subscrib_chnl FROM users WHERE id = ?"
        cursor = await db.execute(query, (user_id,))
        result = await cursor.fetchone()

        if result:
            return result[0]
        else:
            return False

async def get_subscription_status(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status != ChatMemberStatus.LEFT
    except Exception as e:
        print(f"Ошибка при проверке подписки пользователя {user_id}: {e}")
        return False

async def update_subscription_status(user_id, is_subscribed):
    async with aiosqlite.connect('database.db') as db:
        await db.execute("UPDATE users SET subscrib_chnl = ? WHERE id = ?", ('true' if is_subscribed else 'false', user_id))
        await db.commit()


async def get_user_state(user_id):
    async with aiosqlite.connect('database.db') as db:
        cursor = await db.execute('SELECT state FROM use_state WHERE id = ?', (user_id,))
        result = await cursor.fetchone()
    return result[0] if result else None


async def get_user_count():
    async with aiosqlite.connect('database.db') as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            result = await cursor.fetchone()
            user_count = result[0]
            return user_count