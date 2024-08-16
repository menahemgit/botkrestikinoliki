import logging
import random
import string
import json
import asyncio
import time
from datetime import datetime, time as datetime_time
from pathlib import Path
from collections import defaultdict

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'

# ID чата администратора для отправки статистики и ошибок
ADMIN_CHAT_ID = '6592924868'

# Глобальные переменные
active_games = {}
MENU, GAME_PLAY = range(2)
DATA_FILE = Path("game_data.json")
player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0})

# Функции для клавиатур и обработки сообщений
def get_main_keyboard():
    # ... (ваш код для создания основной клавиатуры)
def get_inline_menu_button():
    # ... (ваш код для создания inline-кнопки меню)

def create_board_keyboard(board, game_code):
    # ... (ваш код для создания клавиатуры игрового поля)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для обработки команды /start)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для обработки команды /help)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для показа правил игры)

async def handle_create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для создания новой игры)

async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для присоединения к игре)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для показа статистики)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для показа таблицы лидеров)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для отмены текущего действия)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для обработки текстовых сообщений)

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для обработки хода игрока)

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для обработки хода в игре с ботом)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"An error occurred: {context.error}"
    )

async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE):
    total_games = sum(sum(player.values()) for player in player_stats.values())
    active_players = len(player_stats)
    
    stats_message = (
        f"📊 Ежедневная статистика:\n\n"
        f"Всего игр: {total_games}\n"
        f"Активных игроков: {active_players}\n"
    )
    
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=stats_message)

async def auto_save(context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для автоматического сохранения данных)

async def cleanup_games(context: ContextTypes.DEFAULT_TYPE):
    # ... (ваш код для очистки неактивных игр)

async def load_data():
    # ... (ваш код для загрузки данных)

async def save_data():
    # ... (ваш код для сохранения данных)

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    await load_data()  # Загрузка данных при запуске

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("newgame", handle_create_game))
    application.add_handler(CommandHandler("join", handle_join_game))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("cancel", cancel))

    # Обработчик для открытия меню
    application.add_handler(CallbackQueryHandler(open_menu, pattern='^open_menu$'))

    # Обработчик текстовых сообщений (для кнопок)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики для игрового процесса
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = application.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime_time(hour=3, minute=0))  # Очистка в 3:00 каждый день
    job_queue.run_daily(send_daily_stats, time=datetime_time(hour=0, minute=0))  # Отправка ежедневной статистики в полночь

    # Запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("Bot started")

    # Держим бота запущенным до получения сигнала остановки
    stop_signal = asyncio.Future()
    await stop_signal

    # Остановка бота
    await application.stop()
    await application.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")