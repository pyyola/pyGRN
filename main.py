from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from start_command import register_handlers_start
from add_publication import register_handlers_add_publication
from view_publ import register_handlers_view_publications
from reaction_logic import register_reaction_handlers
from mainpanel import register_handlers_mainpanel
from admin_commands import register_handlers_admin_functions
from config import API_TOKEN
from keyboards import register_handlers
from exceptions import register_handlers_exceptions
from for_advertiser import register_handlers_advertiser_functions


bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
async def main():
    register_handlers_exceptions(dp)
    register_handlers_start(dp)
    register_handlers_add_publication(dp)
    register_handlers_view_publications(dp)
    register_handlers_mainpanel(dp)
    register_reaction_handlers(dp)
    register_handlers_admin_functions(dp)
    register_handlers(dp)
    register_handlers_advertiser_functions(dp)
    await dp.start_polling()


if __name__ == '__main__':
    executor.start(dp, main())
