import logging
import random
import string
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
TOKEN = 'ваш_токен_бота'
EMPTY = '⬜'
X = '❌'
O = '⭕'

# Глобальные переменные для мультиплеера
waiting_players = {}
active_games = {}

def create_board():
    return [EMPTY for _ in range(9)]

def check_winner(board):
    winning_combinations = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # горизонтали
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # вертикали
        (0, 4, 8), (2, 4, 6)              # диагонали
    ]
    for a, b, c in winning_combinations:
        if board[a] == board[b] == board[c] != EMPTY:
            return board[a]
    if EMPTY not in board:
        return 'Tie'
    return None

def create_keyboard(board):
    keyboard = []
    for i in range(0, 9, 3):
        row = [
            InlineKeyboardButton(board[i+j], callback_data=f'move_{i+j}')
            for j in range(3)
        ]
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Одиночная игра", callback_data='single')],
        [InlineKeyboardButton("Мультиплеер", callback_data='multi')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите режим игры:', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'single':
        context.user_data['board'] = create_board()
        context.user_data['current_player'] = X
        await send_board(update, context)
    elif query.data == 'multi':
        await start_multiplayer(update, context)
    elif query.data.startswith('move_'):
        if 'board' in context.user_data:
            await handle_move_single(update, context)
        elif context.user_data.get('game_id') in active_games:
            await handle_move_multi(update, context)

async def send_board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data['board']
    current_player = context.user_data['current_player']
    reply_markup = create_keyboard(board)
    text = f"Ход игрока: {current_player}\n"
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)

async def handle_move_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    move = int(query.data.split('_')[1])
    board = context.user_data['board']
    current_player = context.user_data['current_player']

    if board[move] == EMPTY:
        board[move] = current_player
        winner = check_winner(board)
        if winner:
            await end_game(update, context, winner)
        else:
            context.user_data['current_player'] = O
            await send_board(update, context)
            await bot_move(update, context)
    else:
        await query.answer("Эта клетка уже занята!")

async def bot_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    board = context.user_data['board']
    empty_cells = [i for i, cell in enumerate(board) if cell == EMPTY]
    if empty_cells:
        move = random.choice(empty_cells)
        board[move] = O
        winner = check_winner(board)
        if winner:
            await end_game(update, context, winner)
        else:
            context.user_data['current_player'] = X
            await send_board(update, context)

async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE, winner):
    board = context.user_data['board']
    reply_markup = create_keyboard(board)
    if winner == 'Tie':
        text = "Игра закончилась вничью!"
    else:
        text = f"Игрок {winner} победил!"
    await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
    context.user_data.clear()

async def start_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in waiting_players:
        await update.callback_query.edit_message_text("Вы уже в очереди на игру. Ожидайте соперника.")
    else:
        game_id = f"game_{user_id}"
        waiting_players[user_id] = game_id
        context.user_data['game_id'] = game_id
        active_games[game_id] = {
            'board': create_board(),
            'players': [user_id],
            'current_player': X
        }
        await update.callback_query.edit_message_text("Ожидание второго игрока...")
        await find_opponent(update, context)

async def find_opponent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for opponent_id, opponent_game_id in waiting_players.items():
        if opponent_id != user_id:
            game_id = opponent_game_id
            active_games[game_id]['players'].append(user_id)
            context.user_data['game_id'] = game_id
            del waiting_players[opponent_id]
            if user_id in waiting_players:
                del waiting_players[user_id]
            await start_multiplayer_game(update, context, game_id)
            return
    # Если оппонент не найден, оставляем игрока в очереди

async def start_multiplayer_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    game = active_games[game_id]
    for player_id in game['players']:
        player_context = context.application.user_data.get(player_id, {})
        player_context['game_id'] = game_id
        reply_markup = create_keyboard(game['board'])
        text = f"Игра началась! Ход игрока: {game['current_player']}"
        if player_id == update.effective_user.id:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)

async def handle_move_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    game_id = context.user_data['game_id']
    game = active_games[game_id]
    
    if user_id != game['players'][game['players'].index(X) if game['current_player'] == X else game['players'].index(O)]:
        await query.answer("Сейчас не ваш ход!")
        return

    move = int(query.data.split('_')[1])
    board = game['board']

    if board[move] == EMPTY:
        board[move] = game['current_player']
        winner = check_winner(board)
        if winner:
            await end_multiplayer_game(update, context, game_id, winner)
        else:
            game['current_player'] = O if game['current_player'] == X else X
            await update_multiplayer_board(update, context, game_id)
    else:
        await query.answer("Эта клетка уже занята!")

async def update_multiplayer_board(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    game = active_games[game_id]
    reply_markup = create_keyboard(game['board'])
    text = f"Ход игрока: {game['current_player']}"
    for player_id in game['players']:
        if player_id == update.effective_user.id:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)

async def end_multiplayer_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id, winner):
    game = active_games[game_id]
    reply_markup = create_keyboard(game['board'])
    if winner == 'Tie':
        text = "Игра закончилась вничью!"
    else:
        text = f"Игрок {winner} победил!"
    for player_id in game['players']:
        if player_id == update.effective_user.id:
            await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=player_id, text=text, reply_markup=reply_markup)
    del active_games[game_id]

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.run_polling()

if __name__ == '__main__':
    main()