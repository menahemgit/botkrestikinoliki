import logging
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'

# Состояния для ConversationHandler
MENU, GAME_MODE, PLAYER_NAME, GAME_PLAY, HINTS = range(5)

# Словарь для хранения активных игр
active_games = {}

def start(update: Update, context):
    """Обработчик команды /start."""
    user = update.effective_user
    update.message.reply_text(
        f"Привет, {user.first_name}! Добро пожаловать в игру Крестики-нолики.\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Новая игра", callback_data='new_game')],
            [InlineKeyboardButton("Правила", callback_data='rules')],
            [InlineKeyboardButton("Статистика", callback_data='stats')]
        ])
    )
    return MENU

def menu_handler(update: Update, context):
    """Обработчик кнопок главного меню."""
    query = update.callback_query
    query.answer()
    
    if query.data == 'new_game':
        return game_mode(update, context)
    elif query.data == 'rules':
        return show_rules(update, context)
    elif query.data == 'stats':
        return show_stats(update, context)

def game_mode(update: Update, context):
    """Выбор режима игры."""
    query = update.callback_query
    query.edit_message_text(
        "Выберите режим игры:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Игра с ботом", callback_data='bot_game')],
            [InlineKeyboardButton("Игра с другом", callback_data='friend_game')],
            [InlineKeyboardButton("Назад", callback_data='back_to_menu')]
        ])
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

def handle_create_game(update: Update, context):
    """Обработчик создания новой игры."""
    game_code = create_game(update.effective_user.id)
    update.message.reply_text(
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

def handle_join_game(update: Update, context):
    """Обработчик присоединения к игре."""
    if not context.args:
        update.message.reply_text("Пожалуйста, укажите код игры. Например: /join ABCD")
        return
    
    game_code = context.args[0]
    if join_game(game_code, update.effective_user.id):
        update.message.reply_text(f"Вы присоединились к игре {game_code}!")
        start_game(game_code, context)
    else:
        update.message.reply_text("Игра с таким кодом не найдена или уже заполнена.")

def start_game(game_code, context):
    """Начало игры."""
    game = active_games[game_code]
    context.bot.send_message(game['player1'], "Игра начинается! Вы играете за X.")
    context.bot.send_message(game['player2'], "Игра начинается! Вы играете за O.")
    send_board(game_code, context)

def send_board(game_code, context):
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
    context.bot.send_message(current_player, "Ваш ход:", reply_markup=reply_markup)

# Продолжение следует...

# Продолжение кода...

def handle_move(update: Update, context):
    """Обработка хода игрока."""
    query = update.callback_query
    query.answer()
    
    game_code, move = query.data.split('_')[1:]
    game = active_games.get(game_code)
    
    if not game:
        query.edit_message_text("Эта игра больше не активна.")
        return

    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    
    if query.from_user.id != current_player:
        query.answer("Сейчас не ваш ход!", show_alert=True)
        return

    move = int(move)
    if game['board'][move] == ' ':
        game['board'][move] = game['current_turn']
        game['current_turn'] = 'O' if game['current_turn'] == 'X' else 'X'
        
        winner = check_winner(game['board'])
        if winner:
            end_game(game_code, winner, context)
        elif ' ' not in game['board']:
            end_game(game_code, 'draw', context)
        else:
            send_board(game_code, context)
    else:
        query.answer("Эта клетка уже занята!", show_alert=True)

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

def end_game(game_code, result, context):
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
        context.bot.send_message(game['player1'], "Вы победили!", reply_markup=reply_markup)
        context.bot.send_message(game['player2'], "Вы проиграли.", reply_markup=reply_markup)
    elif result == 'O':
        context.bot.send_message(game['player2'], "Вы победили!", reply_markup=reply_markup)
        context.bot.send_message(game['player1'], "Вы проиграли.", reply_markup=reply_markup)
    else:
        context.bot.send_message(game['player1'], "Ничья!", reply_markup=reply_markup)
        context.bot.send_message(game['player2'], "Ничья!", reply_markup=reply_markup)
    
    del active_games[game_code]

def show_rules(update: Update, context):
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
    update.callback_query.edit_message_text(
        rules_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_menu')]])
    )
    return MENU

def show_stats(update: Update, context):
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
    update.callback_query.edit_message_text(
        stats_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_menu')]])
    )
    return MENU

def cancel(update: Update, context):
    """Отмена текущего действия и возврат в главное меню."""
    update.message.reply_text(
        "Действие отменено. Возвращаемся в главное меню.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Новая игра", callback_data='new_game')],
            [InlineKeyboardButton("Правила", callback_data='rules')],
            [InlineKeyboardButton("Статистика", callback_data='stats')]
        ])
    )
    return MENU

def main():
    """Основная функция запуска бота."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            GAME_MODE: [CallbackQueryHandler(game_mode)],
            GAME_PLAY: [CallbackQueryHandler(handle_move, pattern='^move_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("newgame", handle_create_game))
    dp.add_handler(CommandHandler("join", handle_join_game))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
	
	# Продолжение кода...

import json
from telegram.error import TelegramError

# Функция для сохранения данных
def save_data():
    with open('game_data.json', 'w') as f:
        json.dump({
            'active_games': active_games,
            'player_stats': player_stats,
            'achievements': achievements,
            'daily_tasks': daily_tasks
        }, f)

# Функция для загрузки данных
def load_data():
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
def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        raise context.error
    except TelegramError as e:
        logger.error(f"Telegram Error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

# Периодическое сохранение данных
def auto_save(context):
    save_data()
    logger.info("Auto-saved game data")

# Функция для очистки неактивных игр
def cleanup_games(context):
    current_time = time.time()
    for game_code in list(active_games.keys()):
        if current_time - active_games[game_code].get('last_activity', 0) > 3600:  # 1 час неактивности
            del active_games[game_code]
    logger.info("Cleaned up inactive games")

# Обновленная функция main
def main():
    load_data()  # Загрузка данных при запуске

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

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

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("newgame", handle_create_game))
    dp.add_handler(CommandHandler("join", handle_join_game))

    # Добавление обработчика ошибок
    dp.add_error_handler(error_handler)

    # Настройка периодических задач
    job_queue = updater.job_queue
    job_queue.run_repeating(auto_save, interval=300, first=10)  # Автосохранение каждые 5 минут
    job_queue.run_daily(cleanup_games, time=datetime.time(hour=3, minute=0))  # Очистка в 3:00 каждый день

    updater.start_polling()
    logger.info("Bot started")
    updater.idle()

if __name__ == '__main__':
    main()

# Дополнительные вспомогательные функции

def get_leaderboard():
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['rating'], reverse=True)
    return sorted_players[:10]  # Топ-10 игроков

def show_leaderboard(update: Update, context):
    leaderboard = get_leaderboard()
    leaderboard_text = "Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(leaderboard, 1):
        leaderboard_text += f"{i}. {stats['name']} - {stats['rating']} очков\n"
    update.callback_query.edit_message_text(leaderboard_text)

def help_command(update: Update, context):
    help_text = (
        "Доступные команды:\n"
        "/start - Начать игру или вернуться в главное меню\n"
        "/newgame - Создать новую игру\n"
        "/join [код] - Присоединиться к игре по коду\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать это сообщение\n"
        "/leaderboard - Показать таблицу лидеров"
    )
    update.message.reply_text(help_text)

# Добавление новых обработчиков в main()
dp.add_handler(CommandHandler("help", help_command))
dp.add_handler(CommandHandler("leaderboard", show_leaderboard))

# Функция для обновления времени последней активности игры
def update_game_activity(game_code):
    if game_code in active_games:
        active_games[game_code]['last_activity'] = time.time()

# Обновление функций handle_move и handle_move_with_bot
def handle_move(update: Update, context):
    # ... (существующий код)
    update_game_activity(game_code)
    # ... (остальной код)

def handle_move_with_bot(update: Update, context):
    # ... (существующий код)
    update_game_activity(game_code)
    # ... (остальной код)

# Функция для отправки уведомлений игрокам
def send_notification(context: CallbackContext):
    for player_id, stats in player_stats.items():
        if time.time() - stats.get('last_played', 0) > 86400 * 3:  # Не играл 3 дня
            try:
                context.bot.send_message(player_id, "Давно не виделись! Может, сыграем партию в крестики-нолики?")
            except TelegramError:
                logger.warning(f"Failed to send notification to user {player_id}")

# Добавление задачи отправки уведомлений в main()
job_queue.run_daily(send_notification, time=datetime.time(hour=18, minute=0))  # Отправка уведомлений каждый день в 18:00
