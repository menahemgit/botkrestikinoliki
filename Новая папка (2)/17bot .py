import logging
import random
import string
import json
import asyncio
import time
from datetime import datetime, time as datetime_time

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes
from telegram.ext import filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'

# Глобальные переменные
active_games = {}
MENU, GAME_PLAY = range(2)

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Присоединиться к игре")],
        [KeyboardButton("Правила"), KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_board_keyboard(board, game_code):
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            cell = board[i + j]
            if cell == ' ':
                callback_data = f"move_{game_code}_{i+j}"
            else:
                callback_data = f"occupied_{game_code}_{i+j}"
            row.append(InlineKeyboardButton(cell if cell != ' ' else '.', callback_data=callback_data))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def send_board(game_code, context):
    game = active_games.get(game_code)
    if not game:
        return

    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    opponent = game['player2'] if game['current_turn'] == 'X' else game['player1']

    board_keyboard = create_board_keyboard(game['board'], game_code)
    
    message = f"Игра {game_code}\n"
    message += f"Ход игрока: {context.bot_data['usernames'].get(current_player, 'Неизвестный')} ({game['current_turn']})\n"
    message += f"Ожидает: {context.bot_data['usernames'].get(opponent, 'Неизвестный')} ({'O' if game['current_turn'] == 'X' else 'X'})"

    for player in [game['player1'], game['player2']]:
        try:
            await context.bot.send_message(chat_id=player, text=message, reply_markup=board_keyboard)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение игроку {player}: {e}")

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[1:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.")
        return MENU

    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    
    if query.from_user.id != current_player:
        await query.answer("Сейчас не ваш ход!", show_alert=True)
        return GAME_PLAY

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = game['current_turn']
        game['current_turn'] = 'O' if game['current_turn'] == 'X' else 'X'
        game['last_activity'] = time.time()
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
            return MENU
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
            return MENU
        else:
            await send_board(game_code, context)
            return GAME_PLAY
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)
        return GAME_PLAY

async def end_game(game_code, result, context):
    game = active_games.pop(game_code, None)
    if not game:
        return

    if result == 'draw':
        message = "Игра завершилась вничью!"
    else:
        winner = game['player1'] if result == 'X' else game['player2']
        loser = game['player2'] if result == 'X' else game['player1']
        message = f"Игра завершена! Победитель: {context.bot_data['usernames'].get(winner, 'Неизвестный')} ({result})"

    for player in [game['player1'], game['player2']]:
        try:
            await context.bot.send_message(chat_id=player, text=message)
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры игроку {player}: {e}")

    # Здесь можно добавить обновление статистики игроков

def check_winner(board):
    winning_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # горизонтали
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # вертикали
        [0, 4, 8], [2, 4, 6]  # диагонали
    ]
    for combo in winning_combinations:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != ' ':
            return board[combo[0]]
    return None

async def load_data():
    # Здесь код для загрузки данных при запуске
    pass

async def save_data():
    # Здесь код для сохранения данных при выходе
    pass

async def auto_save(context: ContextTypes.DEFAULT_TYPE):
    # Здесь код для автоматического сохранения
    pass

async def cleanup_games(context: ContextTypes.DEFAULT_TYPE):
    # Здесь код для очистки неактивных игр
    pass
	
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    context.bot_data.setdefault('usernames', {})[user.id] = user.first_name
    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.",
        reply_markup=get_main_keyboard()
    )
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 Доступные команды:\n\n"
        "/start - Начать игру или вернуться в главное меню\n"
        "/newgame - Создать новую игру\n"
        "/join [код] - Присоединиться к игре по коду\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать это сообщение\n"
        "/rules - Показать правила игры"
    )
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    return MENU

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "Правила игры Крестики-нолики:\n\n"
        "1. Игра ведется на поле 3x3.\n"
        "2. Игроки ходят по очереди.\n"
        "3. Первый игрок ставит крестики, второй - нолики.\n"
        "4. Побеждает тот, кто первым выстроит в ряд 3 своих фигуры.\n"
        "5. Если все клетки заполнены, но победитель не определен, объявляется ничья."
    )
    await update.message.reply_text(rules_text, reply_markup=get_main_keyboard())
    return MENU

async def handle_create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    active_games[game_code] = {
        'player1': update.effective_user.id,
        'player2': None,
        'board': [' ' for _ in range(9)],
        'current_turn': 'X',
        'last_activity': time.time()
    }
    await update.message.reply_text(f"Новая игра создана! Код игры: {game_code}")
    return MENU

async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите код игры после команды /join")
        return MENU
    
    game_code = context.args[0].upper()
    game = active_games.get(game_code)
    
    if not game:
        await update.message.reply_text("Игра с таким кодом не найдена.")
        return MENU
    
    if game['player2']:
        await update.message.reply_text("К этой игре уже присоединился второй игрок.")
        return MENU
    
    game['player2'] = update.effective_user.id
    await update.message.reply_text(f"Вы присоединились к игре {game_code}!")
    await start_game(update, context, game_code)
    return GAME_PLAY

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Новая игра":
        return await handle_create_game(update, context)
    elif text == "Присоединиться к игре":
        await update.message.reply_text("Пожалуйста, введите код игры:")
        return MENU
    elif text == "Правила":
        return await show_rules(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    else:
        await update.message.reply_text("Я не понимаю эту команду. Используйте кнопки или /help для списка команд.")
        return MENU

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_code=None):
    if not game_code:
        await update.message.reply_text("Ошибка: не указан код игры.")
        return MENU
    
    game = active_games.get(game_code)
    if not game:
        await update.message.reply_text("Ошибка: игра не найдена.")
        return MENU
    
    await send_board(game_code, context)
    return GAME_PLAY

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Этот функционал нужно реализовать, если вы хотите добавить игру с ботом
    pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("newgame", handle_create_game))
    application.add_handler(CommandHandler("join", handle_join_game))

    # Обработчик текстовых сообщений (для кнопок)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики для игрового процесса
    application.add_handler(CallbackQueryHandler(start_game, pattern='^start_game_'))
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = application.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime_time(hour=3, minute=0))  # Очистка в 3:00 каждый день

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
        pass  # Позволяет корректно завершить работу при нажатии Ctrl+C
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")

import json
from pathlib import Path

DATA_FILE = Path("game_data.json")

async def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            global active_games
            active_games = {k: v for k, v in data.items() if time.time() - v['last_activity'] < 86400}  # Загружаем только игры, созданные не более 24 часов назад
    logger.info("Data loaded successfully")

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(active_games, f)
    logger.info("Data saved successfully")

async def auto_save(context: ContextTypes.DEFAULT_TYPE):
    await save_data()
    logger.info("Auto-save completed")

async def cleanup_games(context: ContextTypes.DEFAULT_TYPE):
    global active_games
    current_time = time.time()
    inactive_games = [code for code, game in active_games.items() if current_time - game['last_activity'] > 86400]
    for code in inactive_games:
        del active_games[code]
    logger.info(f"Cleaned up {len(inactive_games)} inactive games")

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[2:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.")
        return MENU

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = 'X'
        game['last_activity'] = time.time()
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
            return MENU
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
            return MENU
        
        # Ход бота
        bot_move = get_bot_move(game['board'])
        game['board'][bot_move] = 'O'
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
            return MENU
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
            return MENU
        else:
            await send_board(game_code, context)
            return GAME_PLAY
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)
        return GAME_PLAY

def get_bot_move(board):
    empty_cells = [i for i, cell in enumerate(board) if cell == ' ']
    return random.choice(empty_cells)

async def create_bot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    active_games[game_code] = {
        'player1': update.effective_user.id,
        'player2': 'bot',
        'board': [' ' for _ in range(9)],
        'current_turn': 'X',
        'last_activity': time.time()
    }
    await update.message.reply_text(f"Новая игра с ботом создана! Код игры: {game_code}")
    await start_game(update, context, game_code)
    return GAME_PLAY

# Обновляем функцию handle_message
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Новая игра":
        return await handle_create_game(update, context)
    elif text == "Игра с ботом":
        return await create_bot_game(update, context)
    elif text == "Присоединиться к игре":
        await update.message.reply_text("Пожалуйста, введите код игры:")
        return MENU
    elif text == "Правила":
        return await show_rules(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    else:
        await update.message.reply_text("Я не понимаю эту команду. Используйте кнопки или /help для списка команд.")
        return MENU

# Обновляем функцию get_main_keyboard
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Игра с ботом")],
        [KeyboardButton("Присоединиться к игре")],
        [KeyboardButton("Правила"), KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Добавляем новый обработчик в функцию main
application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

from collections import defaultdict

# Глобальные переменные для статистики
player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0})

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = player_stats[user_id]
    total_games = stats["wins"] + stats["losses"] + stats["draws"]
    win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0

    stats_text = (
        f"📊 Ваша статистика:\n\n"
        f"Всего игр: {total_games}\n"
        f"Победы: {stats['wins']}\n"
        f"Поражения: {stats['losses']}\n"
        f"Ничьи: {stats['draws']}\n"
        f"Процент побед: {win_rate:.2f}%"
    )
    await update.message.reply_text(stats_text, reply_markup=get_main_keyboard())
    return MENU

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]["wins"], reverse=True)
    leaderboard_text = "🏆 Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(sorted_players[:10], start=1):
        username = context.bot_data['usernames'].get(player_id, f"Player{player_id}")
        leaderboard_text += f"{i}. {username}: {stats['wins']} побед\n"
    await update.message.reply_text(leaderboard_text, reply_markup=get_main_keyboard())
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено. Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
    return MENU

async def end_game(game_code, result, context):
    game = active_games.pop(game_code, None)
    if not game:
        return

    if result == 'draw':
        message = "Игра завершилась вничью!"
        player_stats[game['player1']]["draws"] += 1
        player_stats[game['player2']]["draws"] += 1
    else:
        winner = game['player1'] if result == 'X' else game['player2']
        loser = game['player2'] if result == 'X' else game['player1']
        message = f"Игра завершена! Победитель: {context.bot_data['usernames'].get(winner, 'Неизвестный')} ({result})"
        player_stats[winner]["wins"] += 1
        player_stats[loser]["losses"] += 1

    for player in [game['player1'], game['player2']]:
        try:
            await context.bot.send_message(chat_id=player, text=message, reply_markup=get_main_keyboard())
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение о завершении игры игроку {player}: {e}")

async def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            global active_games, player_stats
            active_games = {k: v for k, v in data['active_games'].items() if time.time() - v['last_activity'] < 86400}
            player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}, data['player_stats'])
    logger.info("Data loaded successfully")

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            'active_games': active_games,
            'player_stats': dict(player_stats)
        }, f)
    logger.info("Data saved successfully")

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Игра с ботом")],
        [KeyboardButton("Присоединиться к игре"), KeyboardButton("Статистика")],
        [KeyboardButton("Таблица лидеров"), KeyboardButton("Правила")],
        [KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Новая игра":
        return await handle_create_game(update, context)
    elif text == "Игра с ботом":
        return await create_bot_game(update, context)
    elif text == "Присоединиться к игре":
        await update.message.reply_text("Пожалуйста, введите код игры:")
        return MENU
    elif text == "Статистика":
        return await show_stats(update, context)
    elif text == "Таблица лидеров":
        return await show_leaderboard(update, context)
    elif text == "Правила":
        return await show_rules(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    else:
        await update.message.reply_text("Я не понимаю эту команду. Используйте кнопки или /help для списка команд.")
        return MENU

# Обновляем функцию main
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

    # Обработчик текстовых сообщений (для кнопок)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики для игрового процесса
    application.add_handler(CallbackQueryHandler(start_game, pattern='^start_game_'))
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = application.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime_time(hour=3, minute=0))  # Очистка в 3:00 каждый день

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
        pass  # Позволяет корректно завершить работу при нажатии Ctrl+C
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")

import logging
import sys

# Настройка расширенного логирования
def setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root.addHandler(handler)
    
    file_handler = logging.FileHandler('bot.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

# Функция для проверки состояния бота
async def check_bot_status(context: ContextTypes.DEFAULT_TYPE):
    try:
        me = await context.bot.get_me()
        logger.info(f"Bot {me.first_name} is running. Username: @{me.username}")
    except Exception as e:
        logger.error(f"Error checking bot status: {e}")

# Функция для отправки сообщения администратору
async def send_admin_message(context: ContextTypes.DEFAULT_TYPE, message: str):
    admin_id = YOUR_ADMIN_ID  # Замените на ваш ID
    try:
        await context.bot.send_message(chat_id=admin_id, text=message)
    except Exception as e:
        logger.error(f"Failed to send message to admin: {e}")

# Обновленная функция error_handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    await send_admin_message(context, message)

# Функция для периодической проверки и очистки "зависших" игр
async def check_and_clean_stuck_games(context: ContextTypes.DEFAULT_TYPE):
    current_time = time.time()
    stuck_games = [code for code, game in active_games.items() if current_time - game['last_activity'] > 3600]  # 1 час
    for code in stuck_games:
        game = active_games.pop(code)
        for player in [game['player1'], game['player2']]:
            if player != 'bot':
                try:
                    await context.bot.send_message(
                        chat_id=player,
                        text=f"Игра {code} была автоматически завершена из-за отсутствия активности."
                    )
                except Exception as e:
                    logger.error(f"Failed to send message about stuck game to player {player}: {e}")
    if stuck_games:
        logger.info(f"Cleaned up {len(stuck_games)} stuck games")

# Обновленная функция main
async def main() -> None:
    setup_logging()
    
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

    # Обработчик текстовых сообщений (для кнопок)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики для игрового процесса
    application.add_handler(CallbackQueryHandler(start_game, pattern='^start_game_'))
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = application.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime_time(hour=3, minute=0))  # Очистка в 3:00 каждый день
    job_queue.run_repeating(check_bot_status, interval=3600, first=10)  # Проверка статуса бота каждый час
    job_queue.run_repeating(check_and_clean_stuck_games, interval=1800, first=900)  # Проверка "зависших" игр каждые 30 минут

    # Запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("Bot started")
    await send_admin_message(application, "Bot has been started successfully!")

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
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.exception("Exception details:")
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")

	
	
	