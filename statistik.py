import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F, html
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Конфигурация ---
API_TOKEN = '8704131430:AAGkjgqWtdWrwfYHOYhUlrRdoGCEubS9lUc'
ADMIN_ID = 7458899849

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- Логика БД ---
def get_db():
    return sqlite3.connect('chat_stats.db')

def init_db():
    with get_db() as conn:
        # Добавляем хранение user_id, чтобы ссылки на профиль работали всегда
        conn.execute('''CREATE TABLE IF NOT EXISTS messages 
                        (user_id INTEGER, username TEXT, timestamp DATETIME)''')

def log_message(user_id, username):
    with get_db() as conn:
        conn.execute('INSERT INTO messages VALUES (?, ?, ?)', 
                     (user_id, username, datetime.now()))

def fetch_top_users(period_type):
    now = datetime.now()
    if period_type == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period_type == "week":
        start_date = now - timedelta(days=7)
    elif period_type == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    # Получаем username, количество и user_id для создания ссылок
    query = "SELECT username, COUNT(*) as cnt, user_id FROM messages"
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
    
    # Используем HTML теги <b> вместо Markdown
    response = f"🏆 <b>ТОП-15 участников {titles[period]}:</b>\n\n"
    
    if not data:
        response += "<i>Пока здесь пусто...</i>"
    else:
        for i, (name, count, uid) in enumerate(data, 1):
            # Если ника нет, используем ID. html.quote защищает от спецсимволов.
            display_name = name if name else f"User_{uid}"
            user_link = html.link(display_name, f"tg://user?id={uid}")
            
            response += f"{i}. {user_link} — <b>{count}</b> сообщ.\n"
    
    try:
        await callback.message.edit_text(
            text=response, 
            parse_mode="HTML", 
            reply_markup=get_stats_kb(),
            disable_web_page_preview=True # Чтобы не вылазили превью профилей
        )
    except Exception as e:
        # Если вдруг возникнет ошибка (например, сообщение идентично), бот не упадет
        print(f"Ошибка при редактировании: {e}")
    
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
    # Логируем только сообщения из групп/супергрупп от реальных пользователей
    if message.chat.type in ['group', 'supergroup'] and message.from_user and not message.from_user.is_bot:
        log_message(message.from_user.id, message.from_user.username)

async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")
