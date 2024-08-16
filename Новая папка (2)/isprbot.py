from telegram.ext import filters

# Пример использования:
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)