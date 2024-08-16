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
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, ChatMemberHandler
from telegram.ext import filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Токен вашего бота
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'

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

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Новая игра"), KeyboardButton("Игра с ботом")],
        [KeyboardButton("Присоединиться к игре"), KeyboardButton("Статистика")],
        [KeyboardButton("Таблица лидеров"), KeyboardButton("Правила")],
        [KeyboardButton("Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def handle_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.my_chat_member.new_chat_member.status == "member":
        # Это означает, что бот был добавлен в чат или история была очищена
        user = update.effective_user
        welcome_message = (
            f"Здравствуйте, {user.first_name}!\n\n"
            "Я бот для игры в крестики-нолики. Вот что я умею:\n"
            "• Создавать новые игры\n"
            "• Играть с другими игроками\n"
            "• Играть против бота\n"
            "• Показывать статистику и таблицу лидеров\n\n"
            "Чтобы начать, выберите пункт меню или используйте команду /help для получения списка всех команд."
        )
        
        await context.bot.send_message(chat_id=update.effective_chat.id, 
                                       text=welcome_message, 
                                       reply_markup=get_main_keyboard())
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
    game = active_games[game_code]
    board = game['board']
    current_player = game['player1'] if game['current_turn'] == 'X' else game['player2']
    
    board_text = "Текущее состояние игры:\n"
    for i in range(0, 9, 3):
        board_text += f"{board[i]} | {board[i+1]} | {board[i+2]}\n"
        if i < 6:
            board_text += "---------\n"
    
    keyboard = create_board_keyboard(board, game_code)
    
    for player in [game['player1'], game['player2']]:
        if player != 'bot':
            await context.bot.send_message(
                chat_id=player,
                text=f"{board_text}\nХод игрока: {'X' if game['current_turn'] == 'X' else 'O'}",
                reply_markup=keyboard
            )

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

async def load_data():
    global active_games, player_stats
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            active_games = {k: v for k, v in data.get('active_games', {}).items() if time.time() - v['last_activity'] < 86400}
            player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}, data.get('player_stats', {}))
    logger.info("Data loaded successfully")

async def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump({
            'active_games': active_games,
            'player_stats': dict(player_stats)
        }, f)
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        return await join_game(update, context)
    else:
        await update.message.reply_text("Я не понимаю эту команду. Используйте кнопки или /help для списка команд.")
        return MENU

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_code):
    game = active_games.get(game_code)
    if not game:
        await update.message.reply_text("Ошибка: игра не найдена.")
        return MENU
    
    game['current_turn'] = 'X'
    await send_board(game_code, context)
    return GAME_PLAY

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game_code = update.message.text.upper()
    context.user_data['waiting_for_game_code'] = False
    
    game = active_games.get(game_code)
    
    if not game:
        await update.message.reply_text("Игра с таким кодом не найдена.")
        return MENU
    
    if game['player2']:
        await update.message.reply_text("К этой игре уже присоединился второй игрок.")
        return MENU
    
    game['player2'] = update.effective_user.id
    await update.message.reply_text(f"Вы присоединились к игре {game_code}!")
    return await start_game(update, context, game_code)

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
        player_stats
		
async def end_game(game_code, result, context):
    game = active_games.pop(game_code, None)
    if not game:
        return

    if result == 'draw':
        message = "Игра завершилась вничью!"
        player_stats[game['player1']]["draws"] += 1
        if game['player2'] != 'bot':
            player_stats[game['player2']]["draws"] += 1
    else:
        winner = game['player1'] if result == 'X' else game['player2']
        loser = game['player2'] if result == 'X' else game['player1']
        message = f"Игра завершена! Победитель: {context.bot_data['usernames'].get(winner, 'Неизвестный')} ({result})"
        if winner != 'bot':
            player_stats[winner]["wins"] += 1
        if loser != 'bot':
            player_stats[loser]["losses"] += 1

    for player in [game['player1'], game['player2']]:
        if player != 'bot':
            try:
                await context.bot.send_message(chat_id=player, text=message, reply_markup=get_main_keyboard())
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение о завершении игры игроку {player}: {e}")

    await save_data()

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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    # Здесь можно добавить отправку сообщения об ошибке администратору

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
        pass
    finally:
        # Сохранение данных при выходе
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")

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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    # Здесь можно добавить отправку сообщения об ошибке администратору

async def send_daily_stats(context: ContextTypes.DEFAULT_TYPE):
    total_games = sum(len(player['wins'] + player['losses'] + player['draws']) for player in player_stats.values())
    active_players = len(player_stats)
    
    stats_message = (
        f"📊 Ежедневная статистика:\n\n"
        f"Всего игр: {total_games}\n"
        f"Активных игроков: {active_players}\n"
    )
    
    # Здесь вы можете отправить это сообщение администратору или в определенный чат
    # Например:
    # await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=stats_message)

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
    application.add_handler(CallbackQueryHandler(handle_move, pattern='^move_'))
    application.add_handler(CallbackQueryHandler(handle_move_with_bot, pattern='^move_bot_'))

    # Добавляем новый обработчик для изменений в чате
    application.add_handler(ChatMemberHandler(handle_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

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