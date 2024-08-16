import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = 'YOUR_BOT_TOKEN'

# Состояния для ConversationHandler
MENU, GAME_MODE, PLAYER_NAME, GAME_PLAY, HINTS = range(5)

# Словарь для хранения активных игр
active_games = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Новая игра", callback_data='new_game')],
        [InlineKeyboardButton("Правила", callback_data='rules')],
        [InlineKeyboardButton("Статистика", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопок главного меню."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'new_game':
        return await game_mode(update, context)
    elif query.data == 'rules':
        return await show_rules(update, context)
    elif query.data == 'stats':
        return await show_stats(update, context)

async def game_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор режима игры."""
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("Игра с ботом", callback_data='bot_game')],
        [InlineKeyboardButton("Игра с другом", callback_data='friend_game')],
        [InlineKeyboardButton("Назад", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Выберите режим игры:",
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
        'current_turn': 'X'
    }
    return game_code

async def handle_create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик создания новой игры."""
    game_code = create_game(update.effective_user.id)
    await update.message.reply_text(
        f"Новая игра создана! Код игры: {game_code}\n"
        f"Отправьте этот код другу, чтобы он мог присоединиться.\n"
        f"Друг должен использовать команду /join {game_code}"
    )

def join_game(game_code, player2_id):
    """Присоединение к существующей игре."""
    if game_code in active_games and active_games[game_code]['player2'] is None:
        active_games[game_code]['player2'] = player2_id
        return True
    return False

async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик присоединения к игре."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите код игры. Например: /join ABCD")
        return
    
    game_code = context.args[0]
    if join_game(game_code, update.effective_user.id):
        await update.message.reply_text(f"Вы присоединились к игре {game_code}!")
        await start_game(game_code, context)
    else:
        await update.message.reply_text("Игра с таким кодом не найдена или уже заполнена.")

async def start_game(game_code, context: ContextTypes.DEFAULT_TYPE):
    """Начало игры."""
    game = active_games[game_code]
    await context.bot.send_message(game['player1'], "Игра начинается! Вы играете за X.")
    await context.bot.send_message(game['player2'], "Игра начинается! Вы играете за O.")
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
    await context.bot.send_message(current_player, "Ваш ход:", reply_markup=reply_markup)

# Продолжение следует...

# Продолжение кода...

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result == 'X':
        await context.bot.send_message(game['player1'], "Вы победили!", reply_markup=reply_markup)
        await context.bot.send_message(game['player2'], "Вы проиграли.", reply_markup=reply_markup)
    elif result == 'O':
        await context.bot.send_message(game['player2'], "Вы победили!", reply_markup=reply_markup)
        await context.bot.send_message(game['player1'], "Вы проиграли.", reply_markup=reply_markup)
    else:
        await context.bot.send_message(game['player1'], "Ничья!", reply_markup=reply_markup)
        await context.bot.send_message(game['player2'], "Ничья!", reply_markup=reply_markup)
    
    del active_games[game_code]

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать правила игры."""
    rules_text = (
        "Правила игры в Крестики-нолики:\n\n"
        "1. Игра проходит на поле 3x3.\n"
        "2. Игроки ходят по очереди, ставя свой символ (❌ или ⭕) в свободную клетку.\n"
        "3. Цель - собрать три своих символа в ряд (по горизонтали, вертикали или диагонали).\n"
        "4. Побеждает тот, кто первым соберет три символа в ряд.\n"
        "5. Если все клетки заполнены, но никто не победил - это ничья.\n\n"
        "Удачи в игре! 🍀"
    )
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(rules_text, reply_markup=reply_markup)
    return MENU

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать статистику игрока."""
    # Здесь должна быть логика получения статистики игрока из базы данных
    # Пока что просто заглушка
    stats_text = (
        "Ваша статистика:\n\n"
        "Игр сыграно: 0\n"
        "Побед: 0\n"
        "Поражений: 0\n"
        "Ничьих: 0"
    )
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(stats_text, reply_markup=reply_markup)
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия и возврат в главное меню."""
    keyboard = [
        [InlineKeyboardButton("Новая игра", callback_data='new_game')],
        [InlineKeyboardButton("Правила", callback_data='rules')],
        [InlineKeyboardButton("Статистика", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Действие отменено. Возвращаемся в главное меню.",
        reply_markup=reply_markup
    )
    return MENU

# Продолжение следует...

# Продолжение кода...

# Система рейтинга
async def update_rating(player_id, result):
    # Здесь должна быть логика обновления рейтинга игрока
    # Например, +10 за победу, -5 за поражение, +2 за ничью
    pass

# Система достижений
async def check_achievements(player_id):
    # Здесь должна быть логика проверки и выдачи достижений
    # Например, "Первая победа", "10 игр сыграно" и т.д.
    pass

# Ежедневные задания
async def get_daily_tasks(player_id):
    # Здесь должна быть логика генерации и получения ежедневных заданий
    pass

async def complete_daily_task(player_id, task_id):
    # Здесь должна быть логика отметки выполнения ежедневного задания
    pass

# Улучшенная статистика
async def get_detailed_stats(player_id):
    # Здесь должна быть логика получения детальной статистики игрока
    pass

# Функция для игры с ботом
async def play_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = create_game(update.effective_user.id)
    active_games[game_code]['player2'] = 'BOT'
    await update.callback_query.edit_message_text("Игра с ботом начата!")
    await send_board(game_code, context)
    return GAME_PLAY

# Улучшенная функция обработки хода для игры с ботом
async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[1:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.")
        return

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = 'X'
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
            return
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
            return
        
        # Ход бота
        bot_move = get_bot_move(game['board'])
        game['board'][bot_move] = 'O'
        
        winner = check_winner(game['board'])
        if winner:
            await end_game(game_code, winner, context)
        elif ' ' not in game['board']:
            await end_game(game_code, 'draw', context)
        else:
            await send_board(game_code, context)
    else:
        await query.answer("Эта клетка уже занята!", show_alert=True)

def get_bot_move(board):
    # Простая логика для хода бота
    # В будущем можно улучшить, добавив более сложную стратегию
    empty_cells = [i for i, cell in enumerate(board) if cell == ' ']
    return random.choice(empty_cells)

# Обновление главного меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("Новая игра", callback_data='new_game')],
        [InlineKeyboardButton("Играть с ботом", callback_data='play_with_bot')],
        [InlineKeyboardButton("Правила", callback_data='rules')],
        [InlineKeyboardButton("Статистика", callback_data='stats')],
        [InlineKeyboardButton("Достижения", callback_data='achievements')],
        [InlineKeyboardButton("Ежедневные задания", callback_data='daily_tasks')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )
    return MENU

# Обновление обработчика меню
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'new_game':
        return await game_mode(update, context)
    elif query.data == 'play_with_bot':
        return await play_with_bot(update, context)
    elif query.data == 'rules':
        return await show_rules(update, context)
    elif query.data == 'stats':
        return await show_detailed_stats(update, context)
    elif query.data == 'achievements':
        return await show_achievements(update, context)
    elif query.data == 'daily_tasks':
        return await show_daily_tasks(update, context)

# Функции для отображения новых разделов
async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Реализация показа детальной статистики
    stats_text = "Здесь будет отображаться ваша детальная статистика."
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(stats_text, reply_markup=reply_markup)
    return MENU

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Реализация показа достижений
    achievements_text = "Здесь будут отображаться ваши достижения."
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(achievements_text, reply_markup=reply_markup)
    return MENU

async def show_daily_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Реализация показа ежедневных заданий
    tasks_text = "Здесь будут отображаться ваши ежедневные задания."
    keyboard = [[InlineKeyboardButton("Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(tasks_text, reply_markup=reply_markup)
    return MENU

# Продолжение следует...

# Продолжение кода...

import json
import asyncio
from telegram.error import TelegramError

# Функция для сохранения данных
async def save_data():
    with open('game_data.json', 'w') as f:
        json.dump({
            'active_games': active_games,
            'player_stats': player_stats,
            'achievements': achievements,
            'daily_tasks': daily_tasks
        }, f)

# Функция для загрузки данных
async def load_data():
    global active_games, player_stats, achievements, daily_tasks
    try:
        with open('game_data.json', 'r') as f:
            data = json.load(f)
            active_games = data.get('active_games', {})
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

# Функция для отправки уведомлений игрокам
async def send_notification(context: ContextTypes.DEFAULT_TYPE) -> None:
    for player_id, stats in player_stats.items():
        if time.time() - stats.get('last_played', 0) > 86400 * 3:  # Не играл 3 дня
            try:
                await context.bot.send_message(player_id, "Давно не виделись! Может, сыграем партию в крестики-нолики?")
            except TelegramError:
                logger.warning(f"Failed to send notification to user {player_id}")

# Функция для обновления времени последней активности игры
def update_game_activity(game_code):
    if game_code in active_games:
        active_games[game_code]['last_activity'] = time.time()

# Обновление функций handle_move и handle_move_with_bot
async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (существующий код)
    update_game_activity(game_code)
    # ... (остальной код)

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (существующий код)
    update_game_activity(game_code)
    # ... (остальной код)

# Функция для получения таблицы лидеров
def get_leaderboard():
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['rating'], reverse=True)
    return sorted_players[:10]  # Топ-10 игроков

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    leaderboard = get_leaderboard()
    leaderboard_text = "Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(leaderboard, 1):
        leaderboard_text += f"{i}. {stats['name']} - {stats['rating']} очков\n"
    await update.callback_query.edit_message_text(leaderboard_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать игру или вернуться в главное меню\n"
        "/newgame - Создать новую игру\n"
        "/join [код] - Присоединиться к игре по коду\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать это сообщение\n"
        "/leaderboard - Показать таблицу лидеров"
    )
    await update.message.reply_text(help_text)

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
                CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("newgame", handle_create_game))
    application.add_handler(CommandHandler("join", handle_join_game))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("leaderboard", show_leaderboard))

    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = application.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime.time(hour=3, minute=0))  # Очистка в 3:00 каждый день
    job_queue.run_daily(send_notification, time=datetime.time(hour=18, minute=0))  # Отправка уведомлений каждый день в 18:00

    # Запуск бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    logger.info("Bot started")

    # Запуск бота до нажатия Ctrl-C
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    asyncio.run(main())