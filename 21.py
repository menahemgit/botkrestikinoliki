import logging
import random
import string
import json
import asyncio
import time

import random
import string

# ANSI escape коды для цветов
CYAN = '\033[96m'
RESET = '\033[0m'

def generate_game_code():
    # Генерация кода из 6 символов (буквы и цифры)
    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(characters) for _ in range(6))
    return code

# Генерация кода игры
game_code = generate_game_code()

# Вывод кода игры с использованием цвета
print(f"Код игры: {CYAN}{game_code}{RESET}")

from datetime import datetime, time as datetime_time
from pathlib import Path
from collections import defaultdict
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Создаем постоянную клавиатуру
def get_persistent_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Игра с ботом")],
        [KeyboardButton("Присоединиться к игре"), KeyboardButton("Статистика")],
        [KeyboardButton("Таблица лидеров"), KeyboardButton("Правила")],
        [KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.bot_data.setdefault('usernames', {})[user.id] = user.first_name
    welcome_message = (
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n"
        "Выберите действие из меню ниже."
    )
    await update.message.reply_text(welcome_message, reply_markup=get_persistent_keyboard())
    return MENU

async def generate_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = generate_game_code()
    await update.message.reply_text(f"Код игры: `{game_code}`", parse_mode='MarkdownV2')
    print(f"Код игры: {CYAN}{game_code}{RESET}")  # Консольный вывод с цветом

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Новая игра":
        return await create_multiplayer_game(update, context)
    elif text == "Игра с ботом":
        return await create_bot_game(update, context)
    elif text == "Присоединиться к игре":
        await update.message.reply_text("Пожалуйста, введите код игры:", reply_markup=get_persistent_keyboard())
        context.user_data['waiting_for_game_code'] = True
        return MENU
    elif text == "Статистика":
        return await show_stats(update, context)
    elif text == "Таблица лидеров":
        return await show_leaderboard(update, context)
    elif text == "Правила":
        return await show_rules(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    elif context.user_data.get('waiting_for_game_code'):
        context.user_data['waiting_for_game_code'] = False
        return await join_game(update, context)
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Используйте кнопки меню или /help для списка команд.",
            reply_markup=get_persistent_keyboard()
        )
        return MENU

# Обновите все функции, которые отправляют сообщения пользователю, 
# добавив параметр reply_markup=get_persistent_keyboard()
# Например:

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
     # Логика для начала новой игры
    user_id = update.effective_user.id
    stats = player_stats[user_id]
    total_games = stats["wins"] + stats["losses"] + stats["draws"]
    win_rate = (stats["wins"] / total_games * 100) if total_games > 0 else 0

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логика для отображения главного меню

    stats_text = (
        f"📊 Ваша статистика:\n\n"
        f"Всего игр: {total_games}\n"
        f"Победы: {stats['wins']}\n"
        f"Поражения: {stats['losses']}\n"
        f"Ничьи: {stats['draws']}\n"
        f"Процент побед: {win_rate:.2f}%"
    )
    await update.message.reply_text(stats_text, reply_markup=get_persistent_keyboard())
    return MENU

# Обновите функцию main(), добавив обработчик для текстовых сообщений:

async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    await setup_commands(application)
    await load_data()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("newgame", create_multiplayer_game))
    application.add_handler(CommandHandler("botgame", create_bot_game))
    application.add_handler(CommandHandler("join", handle_join_game))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("cancel", cancel))

    # Обработчик текстовых сообщений (для кнопок)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Игра с ботом")],
        [KeyboardButton("Присоединиться к игре"), KeyboardButton("Статистика")],
        [KeyboardButton("Таблица лидеров"), KeyboardButton("Правила")],
        [KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_board_display(board):
    emoji_map = {' ': '⬜️', 'X': '❌', 'O': '⭕️'}
    return '\n'.join([''.join([emoji_map[cell] for cell in board[i:i+3]]) for i in range(0, 9, 3)])

def create_board_keyboard(board, game_code, is_bot_game=False):
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            cell = board[i + j]
            if cell == ' ':
                callback_data = f"move_{'bot_' if is_bot_game else ''}{game_code}_{i+j}"
            else:
                callback_data = f"occupied_{game_code}_{i+j}"
            row.append(InlineKeyboardButton(cell if cell != ' ' else str(i+j+1), callback_data=callback_data))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

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

def bot_move(board):
    empty_cells = [i for i, cell in enumerate(board) if cell == ' ']
    return random.choice(empty_cells)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.bot_data.setdefault('usernames', {})[user.id] = user.first_name
    welcome_message = (
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n"
        "Выберите действие из меню ниже."
    )
    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())
    return MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🆘 Доступные команды:\n\n"
        "/start - Начать игру или вернуться в главное меню\n"
        "/newgame - Создать новую мультиплеерную игру\n"
        "/botgame - Создать новую игру с ботом\n"
        "/join [код] - Присоединиться к игре по коду\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать это сообщение\n"
        "/rules - Показать правила игры\n"
        "/stats - Показать вашу статистику\n"
        "/leaderboard - Показать таблицу лидеров"
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
	
async def create_multiplayer_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    active_games[game_code] = {
        'player1': update.effective_user.id,
        'player2': None,
        'board': [' ' for _ in range(9)],
        'current_turn': 'X',
        'last_activity': time.time()
    }
    await update.message.reply_text(f"Новая мультиплеерная игра создана! Код игры: {game_code}\nПоделитесь этим кодом с другим игроком, чтобы он мог присоединиться.")
    return MENU

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
    await send_board(game_code, context)
    return GAME_PLAY
    
async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, введите код игры:")
    context.user_data['waiting_for_game_code'] = True
    return MENU    

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = update.message.text.upper()
    game = active_games.get(game_code)
    
    if not game:
        await update.message.reply_text("Игра с таким кодом не найдена.")
        return MENU
    
    if game['player2']:
        await update.message.reply_text("К этой игре уже присоединился второй игрок.")
        return MENU
    
    game['player2'] = update.effective_user.id
    await update.message.reply_text(f"Вы присоединились к игре {game_code}!")
    await send_board(game_code, context)
    return GAME_PLAY

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
        bot_move_index = bot_move(game['board'])
        game['board'][bot_move_index] = 'O'
        
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

async def send_board(game_code, context):
    game = active_games[game_code]
    board = game['board']
    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    is_bot_game = game['player2'] == 'bot'
    
    board_display = create_board_display(board)
    keyboard = create_board_keyboard(board, game_code, is_bot_game)
    
    message = f"Текущее состояние игры:\n\n{board_display}\n\nХод игрока: {'X' if game['current_turn'] == 'X' else 'O'}"
    
    for player in [game['player1'], game['player2']]:
        if player != 'bot':
            try:
                await context.bot.send_message(
                    chat_id=player,
                    text=message,
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение игроку {player}: {e}")
                
async def send_game_result(context, chat_id, result, winner=None):
    if result == 'draw':
        message = "Игра завершилась вничью! 🤝"
    else:
        winner_name = context.bot_data['usernames'].get(winner, 'Неизвестный игрок')
        message = f"Игра завершена! Победитель: {winner_name} ({result}) 🏆"
    
    keyboard = [
        [InlineKeyboardButton("Играть снова", callback_data="play_again")],
        [InlineKeyboardButton("Вернуться в главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)                

async def end_game(game_code, result, context):
    game = active_games.pop(game_code, None)
    if not game:
        return

    if result == 'draw':
        await update_player_stats(game['player1'], 'draw')
        await update_player_stats(game['player2'], 'draw')
        winner = None
    else:
        winner = game['player1'] if result == 'X' else game['player2']
        loser = game['player2'] if result == 'X' else game['player1']
        await update_player_stats(winner, 'win')
        await update_player_stats(loser, 'loss')

    for player in [game['player1'], game['player2']]:
        if player != 'bot':
            try:
                await send_game_result(context, player, result, winner)
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение о завершении игры игроку {player}: {e}")

    await save_data()
	
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Новая игра":
        return await create_multiplayer_game(update, context)
    elif text == "Игра с ботом":
        return await create_bot_game(update, context)
    elif text == "Присоединиться к игре":
        await update.message.reply_text("Пожалуйста, введите код игры:")
        context.user_data['waiting_for_game_code'] = True
        return MENU
    elif text == "Статистика":
        return await show_stats(update, context)
    elif text == "Таблица лидеров":
        return await show_leaderboard(update, context)
    elif text == "Правила":
        return await show_rules(update, context)
    elif text == "Помощь":
        return await help_command(update, context)
    elif context.user_data.get('waiting_for_game_code'):
        context.user_data['waiting_for_game_code'] = False
        return await join_game(update, context)
    else:
        await update.message.reply_text(
            "Я не понимаю эту команду. Используйте кнопки меню или /help для списка команд.",
            reply_markup=get_main_keyboard()
        )
        return MENU

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            'active_games': active_games,
            'player_stats': dict(player_stats)
        }, f)
    logger.info("Data saved successfully")

async def load_data():
    global active_games, player_stats
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            active_games = {k: v for k, v in data.get('active_games', {}).items() if time.time() - v['last_activity'] < 86400}
            player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}, data.get('player_stats', {}))
    logger.info("Data loaded successfully")

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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"An error occurred: {context.error}"
    )
    
async def update_player_stats(player, result):
    if player != 'bot':
        if result == 'win':
            player_stats[player]["wins"] += 1
        elif result == 'loss':
            player_stats[player]["losses"] += 1
        else:  # draw
            player_stats[player]["draws"] += 1   
            
async def post_game_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "play_again":
        # Начать новую игру
        await start_game(update, context)
    elif query.data == "main_menu":
        # Вернуться в главное меню
        await show_main_menu(update, context)  
        
                 
    
    
async def main() -> None:
    application = Application.builder().token(TOKEN).build()

    await load_data()  # Загрузка данных при запуске

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))
    application.add_handler(CommandHandler("newgame", create_multiplayer_game))
    application.add_handler(CommandHandler("botgame", create_bot_game))
    application.add_handler(CommandHandler("join", handle_join_game))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(post_game_button_handler, pattern="^(play_again|main_menu)$"))
    
    # Обработчик текстовых сообщений (для кнопок и ввода кода игры)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики для игрового процесса
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_[^bot]'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot'))

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
        pass
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")