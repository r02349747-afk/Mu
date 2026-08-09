import asyncio
import logging
import os
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
POWERUP_EMAIL = os.getenv("POWERUP_EMAIL")       
POWERUP_PASSWORD = os.getenv("POWERUP_PASSWORD") 
SERVER_ID = os.getenv("SERVER_ID")               

if not BOT_TOKEN:
    raise ValueError("ПОМИЛКА: Не знайдено BOT_TOKEN у змінних середовища!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

auto_restart_active = False

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Запустити сервер")],
        [KeyboardButton(text="🔄 Автозапуск: ВИМКНЕНО")]
    ],
    resize_keyboard=True
)

def send_start_request():
    """Миттєвий запит на авторизацію та запуск сервера"""
    if not POWERUP_EMAIL or not POWERUP_PASSWORD or not SERVER_ID:
        return False, "Помилка: На хостингу не налаштовані змінні POWERUP_EMAIL, POWERUP_PASSWORD або SERVER_ID."
    
    try:
        # Використовуємо єдину сесію для швидкого підключення без зайвих рукостискань
        session = requests.Session()
        
        login_url = "https://powerupstack.com/api/auth/login"
        login_response = session.post(login_url, json={
            "email": POWERUP_EMAIL,
            "password": POWERUP_PASSWORD
        }, timeout=5)
        
        if login_response.status_code != 200:
            return False, "Помилка входу в панель (перевір пошту та пароль у налаштуваннях Render)."

        start_url = f"https://powerupstack.com/api/servers/{SERVER_ID}/start"
        start_response = session.post(start_url, timeout=5)
        
        if start_response.status_code == 200:
            return True, "Ваш бот успішно запустився!"
        else:
            return False, "Сервер уже працює або сталася помилка на хостингу."
            
    except requests.exceptions.RequestException as e:
        return False, f"Помилка мережі при зв'язку з хостингом: {e}"

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привіт! Я твій бот-менеджер сервера PowerupStack.\n"
        "Використовуй кнопки нижче для керування:",
        reply_markup=keyboard
    )

@dp.message(F.text == "🚀 Запустити сервер")
async def manual_start(message: Message):
    await message.answer("⏳ Миттєво надсилаю сигнал...")
    # Запускаємо в окремому потоці, щоб телеграм не зависав ні на секунду
    success, text = await asyncio.to_thread(send_start_request)
    await message.answer(text)

@dp.message(F.text.startswith("🔄 Автозапуск:"))
async def toggle_auto_restart(message: Message):
    global auto_restart_active
    auto_restart_active = not auto_restart_active
    
    status_text = "УВІМКНЕНО" if auto_restart_active else "ВИМКНЕНО"
    
    updated_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Запустити сервер")],
            [KeyboardButton(text=f"🔄 Автозапуск: {status_text}")]
        ],
        resize_keyboard=True
    )
    
    if auto_restart_active:
        await message.answer("✅ Автозапуск увімкнено! Бот кожні 5 хвилин перевірятиме і підніматиме сервер, якщо він спить.", reply_markup=updated_keyboard)
    else:
        await message.answer("❌ Автозапуск вимкнено.", reply_markup=updated_keyboard)

@dp.message()
async def unsupported_link(message: Message):
    await message.answer("Эта ссылка не поддерживается.")

async def background_auto_starter():
    """Фоновий процес перевірки 24/7"""
    while True:
        await asyncio.sleep(300) 
        if auto_restart_active:
            try:
                success, text = await asyncio.to_thread(send_start_request)
                if success:
                    logging.info("Автозапуск спрацював успішно: Ваш бот успішно запустився!")
            except Exception as e:
                logging.error(f"Помилка у фоновому автозапуску: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(background_auto_starter())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


