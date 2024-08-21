from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

API_TOKEN = '6317075903:AAExJcIjZFoKvoa9z0tbOEd702GiRh_BwQk'

admin_id = [1414786309]
pusher_ids = [1414786309, 5351012455, 792584311, 6427500914, 792584311]

DATABASE = "database.db"
CHANNEL_ID = -1002023506406

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
