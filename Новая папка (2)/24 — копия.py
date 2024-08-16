from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

# Определение состояний
MENU, GAME = range(2)

def get_persistent_keyboard():
    keyboard = [
        ['Начать игру', 'Сгенерировать код'],
        ['Помощь', 'Выйти']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    welcome_message = (
        "Добро пожаловать в игру Крестики-нолики!\n"
        "Выберите действие из меню ниже."
    )
    await update.message.reply_text(welcome_message, reply_markup=get_persistent_keyboard())
    return MENU

def generate_game_code():
    characters = string.ascii_uppercase + string.digits
    code = ''.join(random.choice(characters) for _ in range(6))
    return code

async def generate_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    game_code = generate_game_code()
    await update.message.reply_text(f"Код игры: `{game_code}`", parse_mode='MarkdownV2')
    print(f"Код игры: {CYAN}{game_code}{RESET}")  # Консольный вывод с цветом
    return MENU

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == 'Начать игру':
        # Логика для начала игры
        await update.message.reply_text("Игра начинается!")
        return GAME
    elif text == 'Сгенерировать код':
        return await generate_code_command(update, context)
    elif text == 'Помощь':
        await update.message.reply_text("Это игра в крестики-нолики. Выберите 'Начать игру' для старта.")
        return MENU
    elif text == 'Выйти':
        await update.message.reply_text("До свидания! Для начала новой игры нажмите /start.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, используйте кнопки меню.")
        return MENU

async def game_logic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Здесь должна быть логика игры в крестики-нолики
    # Пока что просто возвращаемся в меню
    await update.message.reply_text("Игра завершена. Возвращаемся в главное меню.", reply_markup=get_persistent_keyboard())
    return MENU

def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            GAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, game_logic)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()