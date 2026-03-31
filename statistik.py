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

# --- Логика БД ---
def get_db():
    conn = sqlite3.connect('chat_stats.db')
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS messages 
                       (user_id INTEGER, username TEXT, timestamp DATETIME)''')

def log_message(user_id, username):
    with get_db() as conn:
        conn.execute('INSERT INTO messages VALUES (?, ?, ?)', 
                    (user_id, username, datetime.now()))

def fetch_top_users(period_type):
    now = datetime.now()
    if period_type == "day":
        # С начала текущих суток
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == "week":
        # Последние 7 дней
        start_date = now - timedelta(days=7)
    elif period_type == "month":
        # Последние 30 дней
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    query = "SELECT username, COUNT(*) as cnt FROM messages"
    params = []
    if start_date:
        query += " WHERE timestamp > ?"
        params.append(start_date)
    
    query += " GROUP BY user_id ORDER BY cnt DESC LIMIT 15"

    with get_db() as conn:
        return conn.execute(query, params).fetchall()

# --- Клавиатуры ---
def get_stats_kb():
    buttons = [
        [InlineKeyboardButton(text="Сегодня", callback_data="st_day"),
         InlineKeyboardButton(text="Неделя", callback_data="st_week")],
        [InlineKeyboardButton(text="Месяц", callback_data="st_month"),
         InlineKeyboardButton(text="Все время", callback_data="st_all")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Обработчики ---

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    await message.answer("Выберите период для просмотра ТОП-15 активных участников:", 
                         reply_markup=get_stats_kb())

@dp.callback_query(F.data.startswith("st_"))
async def process_stats_callback(callback: types.CallbackQuery):
    period = callback.data.split("_")[1]
    data = fetch_top_users(period)
    
    titles = {"day": "за сегодня", "week": "за неделю", "month": "за месяц", "all": "за все время"}
    
    response = f"🏆 **ТОП-15 участников {titles[period]}:**\n\n"
    if not data:
        response += "Пока здесь пусто..."
    else:
        for i, (name, count) in enumerate(data, 1):
            user = f"@{name}" if name else "Аноним"
            response += f"{i}. {user} — **{count}** сообщ.\n"
    
    # Редактируем сообщение, добавляя кнопки обратно для навигации
    await callback.message.edit_text(response, parse_mode="Markdown", reply_markup=get_stats_kb())
    await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚠️ Полный сброс базы", callback_data="confirm_reset")]
        ])
        await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(F.data == "confirm_reset")
async def reset_stats(callback: types.CallbackQuery):
    if callback.from_user.id == ADMIN_ID:
        with get_db() as conn:
            conn.execute("DELETE FROM messages")
        await callback.answer("База данных очищена!", show_alert=True)
        await callback.message.edit_text("Статистика успешно сброшена.")

@dp.message()
async def tracker(message: types.Message):
    if message.chat.type in ['group', 'supergroup'] and message.from_user:
        log_message(message.from_user.id, message.from_user.username)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
