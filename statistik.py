import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Конфигурация ---
API_TOKEN = '8704131430:AAGkjgqWtdWrwfYHOYhUlrRdoGCEubS9lUc'
ADMIN_ID = 7458899849  # Ваш ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Работа с базой данных ---
def init_db():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            user_id INTEGER,
            username TEXT,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    conn.close()

def log_message(user_id, username):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages VALUES (?, ?, ?)', 
                   (user_id, username, datetime.now()))
    conn.commit()
    conn.close()

def get_stats(period_days=None):
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    
    query = "SELECT username, COUNT(*) as cnt FROM messages"
    params = []
    
    if period_days:
        query += " WHERE timestamp > ?"
        params.append(datetime.now() - timedelta(days=period_days))
    
    query += " GROUP BY user_id ORDER BY cnt DESC LIMIT 10"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

def reset_database():
    conn = sqlite3.connect('stats.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    conn.commit()
    conn.close()

# --- Обработчики ---

# Админ-панель
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Сбросить всю статистику", callback_data="reset_stats")]
        ])
        await message.answer("Добро пожаловать в админ-панель:", reply_markup=kb)
    else:
        await message.answer("У вас нет прав доступа.")

@dp.callback_query(F.data == "reset_stats")
async def process_reset(callback: types.CallbackQuery):
    reset_database()
    await callback.answer("Статистика успешно очищена!", show_alert=True)
    await callback.message.edit_text("Статистика была сброшена.")

# Команда просмотра статистики
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    # Собираем данные по разным периодам
    day = get_stats(1)
    week = get_stats(7)
    month = get_stats(30)
    total = get_stats()

    def format_list(data):
        if not data: return "Нет данных"
        return "\n".join([f"👤 {u if u else 'Incognito'}: {c}" for u, c in data])

    text = (
        f"📊 **Статистика чата**\n\n"
        f"📅 **За 24 часа:**\n{format_list(day)}\n\n"
        f"🗓 **За неделю:**\n{format_list(week)}\n\n"
        f"🗓 **За месяц:**\n{format_list(month)}\n\n"
        f"🏆 **За все время:**\n{format_list(total)}"
    )
    await message.answer(text, parse_mode="Markdown")

# Логирование каждого сообщения
@dp.message()
async def track_messages(message: types.Message):
    if message.chat.type in ['group', 'supergroup']:
        log_message(message.from_user.id, message.from_user.username)

# Запуск
async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())