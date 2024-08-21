from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = 'гавно'

admin_id = [жопа]
pusher_ids = [член]

DATABASE = "database.db"
CHANNEL_ID = ------

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
