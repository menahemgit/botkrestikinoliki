import logging
import random
import string
import json
import asyncio
import time
from datetime import datetime, time as datetime_time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'

# Состояния для ConversationHandler
MENU, GAME_MODE, PLAYER_NAME, GAME_PLAY, HINTS = range(5)

# Словари для хранения данных
active_games = {}
player_stats = {}
achievements = {}
daily_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра", callback_data='new_game')],
        [InlineKeyboardButton("🤖 Играть с ботом", callback_data='play_with_bot')],
        [InlineKeyboardButton("📜 Правила", callback_data='rules')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("🏆 Таблица лидеров", callback_data='leaderboard')],
        [InlineKeyboardButton("🏅 Достижения", callback_data='achievements')],
        [InlineKeyboardButton("📅 Ежедневное задание", callback_data='daily_challenge')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n\n"
        "Выберите действие:\n\n"
        "🎮 Новая игра - Начать новую игру с другим игроком\n"
        "🤖 Играть с ботом - Сыграть против компьютера\n"
        "📜 Правила - Узнать правила игры\n"
        "📊 Статистика - Посмотреть вашу личную статистику\n"
        "🏆 Таблица лидеров - Узнать лучших игроков\n"
        "🏅 Достижения - Ваши личные достижения\n"
        "📅 Ежедневное задание - Получить бонусное задание"
    )
    
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопок главного меню."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'new_game':
        return await game_mode(update, context)
    elif query.data == 'play_with_bot':
        return await play_with_bot(update, context)
    elif query.data == 'rules':
        return await show_rules(update, context)
    elif query.data == 'stats':
        return await show_stats(update, context)
    elif query.data == 'leaderboard':
        return await show_leaderboard(update, context)
    elif query.data == 'achievements':
        return await show_achievements(update, context)
    elif query.data == 'daily_challenge':
        return await daily_challenge(update, context)
    elif query.data == 'back_to_menu':
        return await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать главное меню."""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🎮 Новая игра", callback_data='new_game')],
        [InlineKeyboardButton("🤖 Играть с ботом", callback_data='play_with_bot')],
        [InlineKeyboardButton("📜 Правила", callback_data='rules')],
        [InlineKeyboardButton("📊 Статистика", callback_data='stats')],
        [InlineKeyboardButton("🏆 Таблица лидеров", callback_data='leaderboard')],
        [InlineKeyboardButton("🏅 Достижения", callback_data='achievements')],
        [InlineKeyboardButton("📅 Ежедневное задание", callback_data='daily_challenge')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = (
        "Главное меню:\n\n"
        "🎮 Новая игра - Начать новую игру с другим игроком\n"
        "🤖 Играть с ботом - Сыграть против компьютера\n"
        "📜 Правила - Узнать правила игры\n"
        "📊 Статистика - Посмотреть вашу личную статистику\n"
        "🏆 Таблица лидеров - Узнать лучших игроков\n"
        "🏅 Достижения - Ваши личные достижения\n"
        "📅 Ежедневное задание - Получить бонусное задание"
    )
    await query.edit_message_text(message_text, reply_markup=reply_markup)
    return MENU

async def game_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор режима игры."""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("👥 Игра с другом", callback_data='friend_game')],
        [InlineKeyboardButton("🔍 Случайный соперник", callback_data='random_opponent')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите режим игры:\n\n"
        "👥 Игра с другом - Создайте игру и пригласите друга\n"
        "🔍 Случайный соперник - Найдите случайного соперника для игры\n"
        "◀️ Назад - Вернуться в главное меню",
        reply_markup=reply_markup
    )
    return GAME_MODE

def create_game(player1_id):
    """Создание новой игры."""
    game_code = ''.join(random.choices(string.ascii_uppercase, k=4))
    active_games[game_code] = {
        'player1': player1_id,
        'player2': None,
        'board': [' ' for _ in range(9)],
        'current_turn': 'X',
        'last_activity': time.time()
    }
    return game_code

async def handle_create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания новой игры."""
    game_code = create_game(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Новая игра создана! Код игры: {game_code}\n"
        f"Отправьте этот код другу, чтобы он мог присоединиться.\n"
        f"Друг должен использовать команду /join {game_code}",
        reply_markup=reply_markup
    )

# Продолжение следует...

# Продолжение кода...

def join_game(game_code, player2_id):
    """Присоединение к существующей игре."""
    if game_code in active_games and active_games[game_code]['player2'] is None:
        active_games[game_code]['player2'] = player2_id
        active_games[game_code]['last_activity'] = time.time()
        return True
    return False

async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик присоединения к игре."""
    if not context.args:
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Пожалуйста, укажите код игры. Например: /join ABCD",
            reply_markup=reply_markup
        )
        return
    
    game_code = context.args[0]
    if join_game(game_code, update.effective_user.id):
        keyboard = [[InlineKeyboardButton("Начать игру", callback_data=f'start_game_{game_code}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Вы успешно присоединились к игре {game_code}!",
            reply_markup=reply_markup
        )
    else:
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Игра с таким кодом не найдена или уже заполнена.",
            reply_markup=reply_markup
        )

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры."""
    query = update.callback_query
    await query.answer()
    
    game_code = query.data.split('_')[-1]
    game = active_games[game_code]
    
    await context.bot.send_message(game['player1'], "Игра начинается! Вы играете за ❌.")
    await context.bot.send_message(game['player2'], "Игра начинается! Вы играете за ⭕.")
    
    await send_board(game_code, context)

async def send_board(game_code, context: ContextTypes.DEFAULT_TYPE):
    """Отправка игрового поля."""
    game = active_games[game_code]
    board = game['board']
    keyboard = [
        [InlineKeyboardButton(board[i] or ' ', callback_data=f'move_{game_code}_{i}') for i in range(3)],
        [InlineKeyboardButton(board[i] or ' ', callback_data=f'move_{game_code}_{i}') for i in range(3, 6)],
        [InlineKeyboardButton(board[i] or ' ', callback_data=f'move_{game_code}_{i}') for i in range(6, 9)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    await context.bot.send_message(
        current_player,
        f"Ваш ход ({game['current_turn']}):",
        reply_markup=reply_markup
    )

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка хода игрока."""
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[1:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.")
        return

    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    
    if query.from_user.id != current_player:
        await query.answer("Сейчас не ваш ход!", show_alert=True)
        return

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = game['current_turn']
        game['current_turn'] = 'O' if game['current_turn'] == 'X' else 'X'
        game['last_activity'] = time.time()
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
        else:
            await send_board(game_code, context)
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)

def check_winner(board):
    """Проверка наличия победителя."""
    winning_combinations = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # горизонтали
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # вертикали
        [0, 4, 8], [2, 4, 6]  # диагонали
    ]
    for combo in winning_combinations:
        if board[combo[0]] == board[combo[1]] == board[combo[2]] != ' ':
            return board[combo[0]]
    return None

async def end_game(game_code, result, context: ContextTypes.DEFAULT_TYPE):
    """Завершение игры."""
    game = active_games[game_code]
    board = game['board']
    
    # Отображение финального состояния доски
    keyboard = [
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(3)],
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(3, 6)],
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(6, 9)]
    ]
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result == 'X':
        await context.bot.send_message(game['player1'], "🎉 Вы победили!", reply_markup=reply_markup)
        await context.bot.send_message(game['player2'], "😔 Вы проиграли.", reply_markup=reply_markup)
        await update_stats(game['player1'], 'win')
        await update_stats(game['player2'], 'lose')
    elif result == 'O':
        await context.bot.send_message(game['player2'], "🎉 Вы победили!", reply_markup=reply_markup)
        await context.bot.send_message(game['player1'], "😔 Вы проиграли.", reply_markup=reply_markup)
        await update_stats(game['player2'], 'win')
        await update_stats(game['player1'], 'lose')
    else:
        await context.bot.send_message(game['player1'], "🤝 Ничья!", reply_markup=reply_markup)
        await context.bot.send_message(game['player2'], "🤝 Ничья!", reply_markup=reply_markup)
        await update_stats(game['player1'], 'draw')
        await update_stats(game['player2'], 'draw')
    
    del active_games[game_code]

async def update_stats(player_id, result):
    """Обновление статистики игрока."""
    if player_id not in player_stats:
        player_stats[player_id] = {'wins': 0, 'losses': 0, 'draws': 0}
    
    if result == 'win':
        player_stats[player_id]['wins'] += 1
    elif result == 'lose':
        player_stats[player_id]['losses'] += 1
    else:
        player_stats[player_id]['draws'] += 1

# Продолжение следует...

# Продолжение кода...

async def play_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры с ботом."""
    query = update.callback_query
    await query.answer()
    
    game_code = create_game(update.effective_user.id)
    active_games[game_code]['player2'] = 'BOT'
    
    keyboard = [[InlineKeyboardButton("Начать игру", callback_data=f'start_bot_game_{game_code}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Игра с ботом создана! Нажмите кнопку, чтобы начать.",
        reply_markup=reply_markup
    )
    return GAME_PLAY

async def start_bot_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры с ботом."""
    query = update.callback_query
    await query.answer()
    
    game_code = query.data.split('_')[-1]
    game = active_games[game_code]
    
    await query.edit_message_text("Игра начинается! Вы играете за ❌.")
    await send_board(game_code, context)

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка хода игрока в игре с ботом."""
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[2:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.")
        return

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = 'X'
        game['last_activity'] = time.time()
        
        winner = check_winner(game['board'])
        if winner:
            await end_bot_game(game_code, winner, context)
            return
        elif ' ' not in game['board']:
            await end_bot_game(game_code, 'draw', context)
            return
        
        # Ход бота
        bot_move = get_bot_move(game['board'])
        game['board'][bot_move] = 'O'
        
        winner = check_winner(game['board'])
        if winner:
            await end_bot_game(game_code, winner, context)
        elif ' ' not in game['board']:
            await end_bot_game(game_code, 'draw', context)
        else:
            await send_board(game_code, context)
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)

def get_bot_move(board):
    """Получение хода бота."""
    # Проверяем, может ли бот выиграть следующим ходом
    for i in range(9):
        if board[i] == ' ':
            board[i] = 'O'
            if check_winner(board) == 'O':
                board[i] = ' '
                return i
            board[i] = ' '
    
    # Проверяем, нужно ли блокировать ход игрока
    for i in range(9):
        if board[i] == ' ':
            board[i] = 'X'
            if check_winner(board) == 'X':
                board[i] = ' '
                return i
            board[i] = ' '
    
    # Пытаемся занять центр
    if board[4] == ' ':
        return 4
    
    # Пытаемся занять угол
    corners = [0, 2, 6, 8]
    empty_corners = [i for i in corners if board[i] == ' ']
    if empty_corners:
        return random.choice(empty_corners)
    
    # Занимаем любую свободную клетку
    empty_cells = [i for i in range(9) if board[i] == ' ']
    return random.choice(empty_cells)

async def end_bot_game(game_code, result, context: ContextTypes.DEFAULT_TYPE):
    """Завершение игры с ботом."""
    game = active_games[game_code]
    board = game['board']
    
    # Отображение финального состояния доски
    keyboard = [
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(3)],
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(3, 6)],
        [InlineKeyboardButton(board[i] or ' ', callback_data='_') for i in range(6, 9)]
    ]
    keyboard.append([InlineKeyboardButton("🔄 Играть снова", callback_data='play_with_bot')])
    keyboard.append([InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result == 'X':
        message = "🎉 Поздравляем! Вы победили бота!"
        await update_stats(game['player1'], 'win')
    elif result == 'O':
        message = "😔 К сожалению, бот оказался сильнее. Попробуйте еще раз!"
        await update_stats(game['player1'], 'lose')
    else:
        message = "🤝 Ничья! Хорошая игра!"
        await update_stats(game['player1'], 'draw')
    
    await context.bot.send_message(game['player1'], message, reply_markup=reply_markup)
    del active_games[game_code]

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать таблицу лидеров."""
    query = update.callback_query
    await query.answer()
    
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    leaderboard_text = "🏆 Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(sorted_players[:10], start=1):
        user = await context.bot.get_chat(player_id)
        leaderboard_text += f"{i}. {user.first_name}: {stats['wins']} побед\n"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(leaderboard_text, reply_markup=reply_markup)
    return MENU

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать достижения игрока."""
    query = update.callback_query
    await query.answer()
    
    player_id = query.from_user.id
    stats = player_stats.get(player_id, {'wins': 0, 'losses': 0, 'draws': 0})
    total_games = stats['wins'] + stats['losses'] + stats['draws']
    
    achievements_text = "🏅 Ваши достижения:\n\n"
    if total_games >= 1:
        achievements_text += "🎮 Первая игра\n"
    if stats['wins'] >= 1:
        achievements_text += "🥇 Первая победа\n"
    if total_games >= 10:
        achievements_text += "🏆 Опытный игрок (10+ игр)\n"
    if stats['wins'] >= 5:
        achievements_text += "🌟 Победитель (5+ побед)\n"
    if stats['wins'] >= 10:
        achievements_text += "👑 Мастер игры (10+ побед)\n"
    
    if achievements_text == "🏅 Ваши достижения:\n\n":
        achievements_text += "У вас пока нет достижений. Играйте больше, чтобы получить их!"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(achievements_text, reply_markup=reply_markup)
    return MENU

async def daily_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ежедневное задание."""
    query = update.callback_query
    await query.answer()
    
    player_id = query.from_user.id
    today = datetime.now().date()
    
    if player_id not in daily_tasks or daily_tasks[player_id]['date'] != today:
        daily_tasks[player_id] = {
            'date': today,
            'task': 'Выиграйте одну игру',
            'completed': False
        }
    
    task = daily_tasks[player_id]
    if task['completed']:
        task_text = "🎉 Вы уже выполнили сегодняшнее задание. Возвращайтесь завтра!"
    else:
        task_text = f"📅 Ваше ежедневное задание: {task['task']}"
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(task_text, reply_markup=reply_markup)
    return MENU

# Продолжение следует...

# Продолжение кода...

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать правила игры."""
    query = update.callback_query
    await query.answer()
    
    rules_text = (
        "📜 Правила игры в Крестики-нолики:\n\n"
        "1. Игра проходит на поле 3x3.\n"
        "2. Игроки ходят по очереди, ставя свой символ (❌ или ⭕) в свободную клетку.\n"
        "3. Цель - собрать три своих символа в ряд (по горизонтали, вертикали или диагонали).\n"
        "4. Побеждает тот, кто первым соберет три символа в ряд.\n"
        "5. Если все клетки заполнены, но никто не победил - это ничья.\n\n"
        "Удачи в игре! 🍀"
    )
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(rules_text, reply_markup=reply_markup)
    return MENU

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать статистику игрока."""
    query = update.callback_query
    await query.answer()
    
    player_id = query.from_user.id
    stats = player_stats.get(player_id, {'wins': 0, 'losses': 0, 'draws': 0})
    
    stats_text = (
        "📊 Ваша статистика:\n\n"
        f"🏆 Победы: {stats['wins']}\n"
        f"😔 Поражения: {stats['losses']}\n"
        f"🤝 Ничьи: {stats['draws']}\n"
        f"🎮 Всего игр: {stats['wins'] + stats['losses'] + stats['draws']}"
    )
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(stats_text, reply_markup=reply_markup)
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия и возврат в главное меню."""
    query = update.callback_query
    if query:
        await query.answer()
        await show_main_menu(update, context)
    else:
        await update.message.reply_text("Действие отменено. Возвращаемся в главное меню.")
        await start(update, context)
    return MENU

# Функция для сохранения данных
async def save_data():
    data = {
        'player_stats': player_stats,
        'achievements': achievements,
        'daily_tasks': daily_tasks
    }
    with open('game_data.json', 'w') as f:
        json.dump(data, f)

# Функция для загрузки данных
async def load_data():
    global player_stats, achievements, daily_tasks
    try:
        with open('game_data.json', 'r') as f:
            data = json.load(f)
            player_stats = data.get('player_stats', {})
            achievements = data.get('achievements', {})
            daily_tasks = data.get('daily_tasks', {})
    except FileNotFoundError:
        logger.info("Data file not found. Starting with empty data.")

# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        raise context.error
    except TelegramError as e:
        logger.error(f"Telegram Error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

# Периодическое сохранение данных
async def auto_save(context: ContextTypes.DEFAULT_TYPE) -> None:
    await save_data()
    logger.info("Auto-saved game data")

# Функция для очистки неактивных игр
async def cleanup_games(context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = time.time()
    for game_code in list(active_games.keys()):
        if current_time - active_games[game_code].get('last_activity', 0) > 3600:  # 1 час неактивности
            del active_games[game_code]
    logger.info("Cleaned up inactive games")

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
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(help_text, reply_markup=reply_markup)

# ... (предыдущий код остается без изменений)

# Основная функция для запуска бота
async def main() -> None:
    await load_data()  # Загрузка данных при запуске

    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            GAME_MODE: [CallbackQueryHandler(game_mode)],
            GAME_PLAY: [
                CallbackQueryHandler(handle_move, pattern='^move_'),
                CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'),
                CallbackQueryHandler(start_game, pattern='^start_game_'),
                CallbackQueryHandler(start_bot_game, pattern='^start_bot_game_')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("newgame", handle_create_game))
    application.add_handler(CommandHandler("join", handle_join_game))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", show_rules))

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