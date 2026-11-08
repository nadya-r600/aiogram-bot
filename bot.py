import asyncio
from os import getenv
from datetime import datetime

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from database import init_db, get_homework, delete_passed_homework, clear_old_overrides
from handlers.routers import router

# Загружаем переменные окружения (токен бота)
load_dotenv()
TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()
dp.include_router(router) # Подключаем все команды и кнопки

# Фоновая задача: напоминание про ДЗ по воскресеньям в 18:00
async def weekly_reminder(bot: Bot, admin_id: int):
    while True:
        now = datetime.now()
        # 6 = воскресенье. Если сегодня ВС и время с 18:00 до 18:05
        if now.weekday() == 6 and now.hour == 18 and now.minute < 5:
            rows = await get_homework()
            if rows:
                text = "🔔 <b>Напоминание на неделю!</b>\n\nНе забудь про ДЗ:\n"
                for hw_id, subj, task, deadline, done in rows:
                    if not done:
                        text += f"🔴 <b>{subj}</b>: {task} (до {deadline})\n"
                try:
                    await bot.send_message(admin_id, text, parse_mode="HTML")
                except Exception as e:
                    print("Ошибка отправки напоминания:", e)
            
            # Очищаем просроченное ДЗ и старые изменения расписания
            await delete_passed_homework()
            await clear_old_overrides()
            
        await asyncio.sleep(60) # Проверяем каждую минуту

async def main():
    # Создаем таблицы в базе данных при запуске
    await init_db()
    
    bot = Bot(token=TOKEN)
    
    # Твой Telegram ID (нужен для напоминаний). Узнать можно у @userinfobot
    ADMIN_ID = int(getenv("ADMIN_ID", "123456789"))
    
    # Запускаем фоновую задачу для напоминаний
    asyncio.create_task(weekly_reminder(bot, ADMIN_ID))
    
    print("Start...")
    await dp.start_polling(bot)

# --- ЭТА СТРОКА ЗАПУСКАЕТ БОТА ---
if __name__ == "__main__":
    asyncio.run(main())