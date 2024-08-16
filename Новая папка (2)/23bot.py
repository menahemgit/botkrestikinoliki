import logging
import random
import json
import asyncio
from pathlib import Path
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
TOKEN = '7285079982:AAF7h-dP_WbeHQjOUYr-BvTtR02GJHkBmtQ'
DATA_FILE = Path('game_data.json')

def check_winner(board):
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Горизонтали
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Вертикали
        (0, 4, 8), (2, 4, 6)              # Диагонали
    ]
    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] != ' ':
            return board[a]
    return None

def bot_move(board):
    for i in range(9):
        if board[i] == ' ':
            board[i] = 'O'
            if check_winner(board) == 'O':
                board[i] = ' '
                return i
            board[i] = ' '
    
    for i in range(9):
        if board[i] == ' ':
            board[i] = 'X'
            if check_winner(board) == 'X':
                board[i] = ' '
                return i
            board[i] = ' '
    
    empty_cells = [i for i, cell in enumerate(board) if cell == ' ']
    return random.choice(empty_cells)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я бот для игры в крестики-нолики. Напиши /tictactoe, чтобы начать игру.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Доступные команды:\n/start - Начать\n/help - Помощь\n/tictactoe - Играть в крестики-нолики')

async def start_tictactoe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tictactoe_board'] = [' ' for _ in range(9)]
    context.user_data['current_player'] = 'X'
    await send_tictactoe_board(update, context)

async def send_tictactoe_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data['tictactoe_board']
    keyboard = [
        [InlineKeyboardButton(board[i*3+j] if board[i*3+j] != ' ' else '_', callback_data=f'ttt_{i*3+j}') for j in range(3)]
        for i in range(3)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Крестики-нолики:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Крестики-нолики:", reply_markup=reply_markup)

async def tictactoe_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    move = int(query.data.split('_')[1])
    board = context.user_data['tictactoe_board']
    current_player = context.user_data['current_player']

    if board[move] == ' ':
        board[move] = current_player
        winner = check_winner(board)
        if winner:
            await query.edit_message_text(f"Игрок {winner} победил!")
            return
        if ' ' not in board:
            await query.edit_message_text("Ничья!")
            return
        
        context.user_data['current_player'] = 'O'
        await send_tictactoe_board(update, context)
        
        # Ход бота
        bot_move_index = bot_move(board)
        board[bot_move_index] = 'O'
        winner = check_winner(board)
        if winner:
            await send_tictactoe_board(update, context)
            await query.message.reply_text(f"Бот победил!")
            return
        if ' ' not in board:
            await send_tictactoe_board(update, context)
            await query.message.reply_text("Ничья!")
            return
        
        context.user_data['current_player'] = 'X'
        await send_tictactoe_board(update, context)
    else:
        await query.answer("Эта клетка уже занята!")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, я не знаю такой команды.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, я не понимаю обычный текст. Используйте команды, начинающиеся с /")

async def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            # Здесь можно загрузить сохраненные данные, если они нужны
    logger.info("Data loaded successfully")

async def save_data():
    data = {
        # Здесь можно сохранить нужные данные
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)
    logger.info("Data saved successfully")

async def main():
    await load_data()
    
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tictactoe", start_tictactoe))

    # Обработчик для игры "Крестики-нолики"
    application.add_handler(CallbackQueryHandler(tictactoe_button, pattern="^ttt_"))

    # Обработчик для неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Обработчик для обычных текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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
        asyncio.run(save_data())
        logger.info("Bot stopped and data saved")

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

async def send_board(game_code, context):
    game = active_games[game_code]
    board = game['board']
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

async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[1:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.", reply_markup=get_persistent_keyboard())
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

async def handle_move_with_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    game_code, move = query.data.split('_')[2:]
    game = active_games.get(game_code)
    
    if not game:
        await query.edit_message_text("Эта игра больше не активна.", reply_markup=get_persistent_keyboard())
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
                await context.bot.send_message(chat_id=player, text=message, reply_markup=get_persistent_keyboard())
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение о завершении игры игроку {player}: {e}")

    await save_data()

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]["wins"], reverse=True)
    leaderboard_text = "🏆 Таблица лидеров:\n\n"
    for i, (player_id, stats) in enumerate(sorted_players[:10], start=1):
        username = context.bot_data['usernames'].get(player_id, f"Player{player_id}")
        leaderboard_text += f"{i}. {username}: {stats['wins']} побед\n"
    await update.message.reply_text(leaderboard_text, reply_markup=get_persistent_keyboard())
    return MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено. Возвращаемся в главное меню.", reply_markup=get_persistent_keyboard())
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
            active_games = {k: v for k, v in data.get('active_games', {}).items() if time.time() - v['last_activity'] < INACTIVE_GAME_TIMEOUT}
            player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}, data.get('player_stats', {}))
    logger.info("Data loaded successfully")

async def auto_save(context: ContextTypes.DEFAULT_TYPE):
    await save_data()
    logger.info("Auto-save completed")

async def cleanup_games(context: ContextTypes.DEFAULT_TYPE):
    global active_games
    current_time = time.time()
    inactive_games = [code for code, game in active_games.items() if current_time - game['last_activity'] > INACTIVE_GAME_TIMEOUT]
    for code in inactive_games:
        del active_games[code]
    logger.info(f"Cleaned up {len(inactive_games)} inactive games")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception while handling an update: {context.error}")
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"An error occurred: {context.error}"
    )
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
    
   # ... (весь предыдущий код)

async def load_data():
    global active_games, player_stats
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            active_games = {k: v for k, v in data.get('active_games', {}).items() if time.time() - v['last_activity'] < INACTIVE_GAME_TIMEOUT}
            player_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0}, data.get('player_stats', {}))
    logger.info("Data loaded successfully")

async def start_tictactoe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['tictactoe_board'] = [' ' for _ in range(9)]
    context.user_data['current_player'] = 'X'
    await send_tictactoe_board(update, context)

async def send_tictactoe_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data['tictactoe_board']
    keyboard = [
        [InlineKeyboardButton(board[i*3+j] if board[i*3+j] != ' ' else '_', callback_data=f'ttt_{i*3+j}') for j in range(3)]
        for i in range(3)
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Крестики-нолики:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Крестики-нолики:", reply_markup=reply_markup)

async def tictactoe_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    move = int(query.data.split('_')[1])
    board = context.user_data['tictactoe_board']
    current_player = context.user_data['current_player']

    if board[move] == ' ':
        board[move] = current_player
        winner = check_winner(board)
        if winner:
            await query.edit_message_text(f"Игрок {winner} победил!")
            return
        if ' ' not in board:
            await query.edit_message_text("Ничья!")
            return
        
        context.user_data['current_player'] = 'O'
        await send_tictactoe_board(update, context)
        
        # Ход бота
        bot_move_index = bot_move(board)
        board[bot_move_index] = 'O'
        winner = check_winner(board)
        if winner:
            await send_tictactoe_board(update, context)
            await query.message.reply_text(f"Бот победил!")
            return
        if ' ' not in board:
            await send_tictactoe_board(update, context)
            await query.message.reply_text("Ничья!")
            return
        
        context.user_data['current_player'] = 'X'
        await send_tictactoe_board(update, context)
    else:
        await query.answer("Эта клетка уже занята!")
    
async def main():
    await load_data()
    
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("tictactoe", start_tictactoe))

    # Обработчики для игры "Угадай число"
    application.add_handler(CommandHandler("guess", start_guess_game))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guess))

    # Обработчик для игры "Крестики-нолики"
    application.add_handler(CallbackQueryHandler(tictactoe_button, pattern="^ttt_"))

    # Обработчик для неизвестных команд
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Обработчик для обычных текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

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