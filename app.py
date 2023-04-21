import os
from dotenv import load_dotenv
import openai
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
)
import re

load_dotenv()

# Configurar OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

# Estados de conversación
LANGUAGE, REMINDER = range(2)

# Función para generar respuestas usando GPT-3
def gpt3_generate(prompt):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.7,
    )

    message = response.choices[0].text.strip()
    return message

# Funciones de manejo de Telegram
def start(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("English", callback_data="en"),
            InlineKeyboardButton("Español", callback_data="es"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text("Please choose your language:", reply_markup=reply_markup)

    return LANGUAGE

def set_language(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    query.edit_message_text("Language set. What can I do for you?")

    return REMINDER

def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    gpt3_response = gpt3_generate(user_message)
    update.message.reply_text(gpt3_response)

def process_reminder(update: Update, context: CallbackContext):
    text = update.message.text
    match = re.match(r'^/reminder (.+) (\d{4}-\d{2}-\d{2} \d{2}:\d{2})$', text)
    if match:
        reminder_text, reminder_time = match.groups()
        reminder_datetime = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M")
        now = datetime.now()
        if reminder_datetime < now:
            update.message.reply_text("Sorry, I cannot set a reminder for the past.")
        else:
            context.job_queue.run_once(send_reminder, (reminder_datetime - now).total_seconds(), context={"chat_id": update.message.chat_id, "text": reminder_text})
            update.message.reply_text(f"Reminder set for {reminder_time}.")
    else:
        update.message.reply_text("Invalid reminder format. Please use: /reminder <reminder text> <YYYY-MM-DD HH:MM>")

def send_reminder(context: CallbackContext):
    job = context.job
    reminder_text = job.context["text"]
    context.bot.send_message(job.context["chat_id"], text=reminder_text)

def main():
    updater = Updater(os.getenv("TELEGRAM_API_TOKEN"))

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CallbackQueryHandler(set_language, pattern="^(en|es)$"))

    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    reminder_handler = ConversationHandler(
        entry_points=[CommandHandler("reminder", process_reminder)],
        states={REMINDER: [MessageHandler(Filters.text, process_reminder)]},
        fallbacks=[],
    )
    dispatcher.add_handler(reminder_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
