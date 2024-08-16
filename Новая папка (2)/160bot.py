import logging
import random
import string
import json
import asyncio
import time
from datetime import datetime, time as datetime_time

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
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

# Определение клавиатуры с постоянными кнопками
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("🎮 Новая игра"), KeyboardButton("🤖 Играть с ботом")],
        [KeyboardButton("📜 Правила"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("🏆 Таблица лидеров"), KeyboardButton("🏅 Достижения")],
        [KeyboardButton("📅 Ежедневное задание")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
	
	# Добавьте функцию start здесь
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.",
        reply_markup=get_main_keyboard()
    )
    return MENU


# Добавьте эту функцию перед функцией main()

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

# Остальной код остается без изменений

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик текстовых сообщений."""
    text = update.message.text
    if text == "🎮 Новая игра":
        return await game_mode(update, context)
    elif text == "🤖 Играть с ботом":
        return await play_with_bot(update, context)
    elif text == "📜 Правила":
        return await show_rules(update, context)
    elif text == "📊 Статистика":
        return await show_stats(update, context)
    elif text == "🏆 Таблица лидеров":
        return await show_leaderboard(update, context)
    elif text == "🏅 Достижения":
        return await show_achievements(update, context)
    elif text == "📅 Ежедневное задание":
        return await daily_challenge(update, context)
    elif text == "👥 Игра с другом":
        return await handle_create_game(update, context)
    elif text == "🔍 Случайный соперник":
        # Здесь нужно реализовать логику для поиска случайного соперника
        await update.message.reply_text("Поиск случайного соперника пока не реализован.", reply_markup=get_main_keyboard())
        return MENU
    elif text == "◀️ Назад":
        await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
        return MENU
    else:
        await update.message.reply_text("Извините, я не понимаю эту команду.", reply_markup=get_main_keyboard())
        return MENU

async def game_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор режима игры."""
    keyboard = [
        [KeyboardButton("👥 Игра с другом"), KeyboardButton("🔍 Случайный соперник")],
        [KeyboardButton("◀️ Назад")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
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
    await update.message.reply_text(
        f"Новая игра создана! Код игры: {game_code}\n"
        f"Отправьте этот код другу, чтобы он мог присоединиться.\n"
        f"Друг должен использовать команду /join {game_code}",
        reply_markup=get_main_keyboard()
    )
    return MENU

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
        await update.message.reply_text(
            "Пожалуйста, укажите код игры. Например: /join ABCD",
            reply_markup=get_main_keyboard()
        )
        return MENU
    
    game_code = context.args[0]
    if join_game(game_code, update.effective_user.id):
        keyboard = [[InlineKeyboardButton("Начать игру", callback_data=f'start_game_{game_code}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Вы успешно присоединились к игре {game_code}!",
            reply_markup=reply_markup
        )
        return GAME_PLAY
    else:
        await update.message.reply_text(
            "Игра с таким кодом не найдена или уже заполнена.",
            reply_markup=get_main_keyboard()
        )
        return MENU

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры."""
    query = update.callback_query
    await query.answer()
    
    game_code = query.data.split('_')[-1]
    game = active_games[game_code]
    
    await context.bot.send_message(game['player1'], "Игра начинается! Вы играете за ❌.")
    await context.bot.send_message(game['player2'], "Игра начинается! Вы играете за ⭕.")
    
    await send_board(game_code, context)
    return GAME_PLAY

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

# ... (предыдущий код)

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код функции handle_move)

# Добавьте функцию handle_move_with_bot здесь

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка хода игрока."""
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

# Предыдущий код...

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка хода игрока."""
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
    """Обработка хода игрока в игре с ботом."""
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
            await end_bot_game(game_code, winner, context)
            return MENU
        elif ' ' not in game['board']:
            await end_bot_game(game_code, 'draw', context)
            return MENU
        
        # Ход бота
        bot_move = get_bot_move(game['board'])
        game['board'][bot_move] = 'O'
        
        winner = check_winner(game['board'])
        if winner:
            await end_bot_game(game_code, winner, context)
            return MENU
        elif ' ' not in game['board']:
            await end_bot_game(game_code, 'draw', context)
            return MENU
        else:
            await send_board(game_code, context)
            return GAME_PLAY
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)
        return GAME_PLAY

# Следующий код...

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

# Продолжение следует...

# Продолжение кода...

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
    
    await update_achievements(player_id)
    await check_daily_task(player_id, result)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать таблицу лидеров."""
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['wins'], reverse=True)
    leaderboard_text = "🏆 Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(sorted_players[:10], start=1):
        user = await context.bot.get_chat(player_id)
        leaderboard_text += f"{i}. {user.first_name}: {stats['wins']} побед\n"
    
    await update.message.reply_text(leaderboard_text, reply_markup=get_main_keyboard())
    return MENU

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать достижения игрока."""
    player_id = update.effective_user.id
    player_achievements = achievements.get(player_id, set())
    
    achievements_text = "🏅 Ваши достижения:\n\n"
    if 'first_game' in player_achievements:
        achievements_text += "🎮 Первая игра\n"
    if 'first_win' in player_achievements:
        achievements_text += "🥇 Первая победа\n"
    if 'experienced_player' in player_achievements:
        achievements_text += "🏆 Опытный игрок (10+ игр)\n"
    if 'winner' in player_achievements:
        achievements_text += "🌟 Победитель (5+ побед)\n"
    if 'master' in player_achievements:
        achievements_text += "👑 Мастер игры (10+ побед)\n"
    
    if not player_achievements:
        achievements_text += "У вас пока нет достижений. Играйте больше, чтобы получить их!"
    
    await update.message.reply_text(achievements_text, reply_markup=get_main_keyboard())
    return MENU

async def daily_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ежедневное задание."""
    player_id = update.effective_user.id
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
    
    await update.message.reply_text(task_text, reply_markup=get_main_keyboard())
    return MENU

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать правила игры."""
    rules_text = (
        "📜 Правила игры в Крестики-нолики:\n\n"
        "1. Игра проходит на поле 3x3.\n"
        "2. Игроки ходят по очереди, ставя свой символ (❌ или ⭕) в свободную клетку.\n"
        "3. Цель - собрать три своих символа в ряд (по горизонтали, вертикали или диагонали).\n"
        "4. Побеждает тот, кто первым соберет три символа в ряд.\n"
        "5. Если все клетки заполнены, но никто не победил - это ничья.\n\n"
        "Удачи в игре! 🍀"
    )
    await update.message.reply_text(rules_text, reply_markup=get_main_keyboard())
    return MENU

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать статистику игрока."""
    player_id = update.effective_user.id
    stats = player_stats.get(player_id, {'wins': 0, 'losses': 0, 'draws': 0})
    
    stats_text = (
        "📊 Ваша статистика:\n\n"
        f"🏆 Победы: {stats['wins']}\n"
        f"😔 Поражения: {stats['losses']}\n"
        f"🤝 Ничьи: {stats['draws']}\n"
        f"🎮 Всего игр: {stats['wins'] + stats['losses'] + stats['draws']}"
    )
    await update.message.reply_text(stats_text, reply_markup=get_main_keyboard())
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия и возврат в главное меню."""
    await update.message.reply_text("Действие отменено. Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
    return MENU

# Продолжение следует...

# Продолжение кода...

async def update_achievements(player_id):
    """Обновление достижений игрока."""
    if player_id not in achievements:
        achievements[player_id] = set()
    
    stats = player_stats.get(player_id, {'wins': 0, 'losses': 0, 'draws': 0})
    total_games = stats['wins'] + stats['losses'] + stats['draws']
    
    if total_games >= 1 and 'first_game' not in achievements[player_id]:
        achievements[player_id].add('first_game')
        await notify_achievement(player_id, "🎮 Первая игра")
    
    if stats['wins'] >= 1 and 'first_win' not in achievements[player_id]:
        achievements[player_id].add('first_win')
        await notify_achievement(player_id, "🥇 Первая победа")
    
    if total_games >= 10 and 'experienced_player' not in achievements[player_id]:
        achievements[player_id].add('experienced_player')
        await notify_achievement(player_id, "🏆 Опытный игрок (10+ игр)")
    
    if stats['wins'] >= 5 and 'winner' not in achievements[player_id]:
        achievements[player_id].add('winner')
        await notify_achievement(player_id, "🌟 Победитель (5+ побед)")
    
    if stats['wins'] >= 10 and 'master' not in achievements[player_id]:
        achievements[player_id].add('master')
        await notify_achievement(player_id, "👑 Мастер игры (10+ побед)")

async def notify_achievement(player_id, achievement_text):
    """Уведомление о новом достижении."""
    await application.bot.send_message(
        player_id,
        f"🎉 Поздравляем! Вы получили новое достижение:\n{achievement_text}"
    )

async def check_daily_task(player_id, result):
    """Проверка и обновление ежедневного задания."""
    today = datetime.now().date()
    if player_id in daily_tasks and daily_tasks[player_id]['date'] == today:
        task = daily_tasks[player_id]
        if not task['completed']:
            if (task['task'] == 'Выиграйте одну игру' and result == 'win') or \
               (task['task'] == 'Сыграйте одну игру' and result in ['win', 'lose', 'draw']):
                task['completed'] = True
                await application.bot.send_message(
                    player_id,
                    "🎉 Поздравляем! Вы выполнили ежедневное задание!"
                )

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать правила игры."""
    rules_text = (
        "📜 Правила игры в Крестики-нолики:\n\n"
        "1. Игра проходит на поле 3x3.\n"
        "2. Игроки ходят по очереди, ставя свой символ (❌ или ⭕) в свободную клетку.\n"
        "3. Цель - собрать три своих символа в ряд (по горизонтали, вертикали или диагонали).\n"
        "4. Побеждает тот, кто первым соберет три символа в ряд.\n"
        "5. Если все клетки заполнены, но никто не победил - это ничья.\n\n"
        "Удачи в игре! 🍀"
    )
    await update.message.reply_text(rules_text, reply_markup=get_main_keyboard())
    return MENU

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать статистику игрока."""
    player_id = update.effective_user.id
    stats = player_stats.get(player_id, {'wins': 0, 'losses': 0, 'draws': 0})
    
    stats_text = (
        "📊 Ваша статистика:\n\n"
        f"🏆 Победы: {stats['wins']}\n"
        f"😔 Поражения: {stats['losses']}\n"
        f"🤝 Ничьи: {stats['draws']}\n"
        f"🎮 Всего игр: {stats['wins'] + stats['losses'] + stats['draws']}"
    )
    await update.message.reply_text(stats_text, reply_markup=get_main_keyboard())
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия и возврат в главное меню."""
    await update.message.reply_text("Действие отменено. Возвращаемся в главное меню.", reply_markup=get_main_keyboard())
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

# Основная функция для запуска бота
async def main() -> None:
    global application
    await load_data()  # Загрузка данных при запуске

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
		