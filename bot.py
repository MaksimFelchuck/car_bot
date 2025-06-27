from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

import os

TOKEN = os.environ["TOKEN"]


QUESTION_1, QUESTION_2, QUESTION_3, QUESTION_4, RESULT = range(5)

# Описание вопросов и ключевых значений
QUESTIONS = [
    ("Какой у вас бюджет на покупку автомобиля?", "budget"),
    ("Вы предпочитаете седан, хэтчбек, внедорожник или кроссовер?", "body_type"),
    ("Выбираете автомат или механику?", "transmission"),
    ("Рассматриваете только новые машины или подойдут и б/у?", "condition"),
]

# Варианты ответов для каждого вопроса
ANSWER_OPTIONS = {
    0: ["до 500,000", "500,000 - 1,000,000", "более 1,000,000"],
    1: ["Седан", "Хэтчбек", "Внедорожник", "Кроссовер"],
    2: ["Автомат", "Механика"],
    3: ["Только новые", "Новые и б/у"],
}

class CarBot:
    def __init__(self, token: str):
        self.app = ApplicationBuilder().token(token).build()
        self.user_answers = {}

        # Обработчики команд
        self.app.add_handler(CommandHandler("start", self.start))

        # Обработчик кнопок
        self.app.add_handler(CallbackQueryHandler(self.handle_answer))

        # Разворачиваем ConversationHandler для вопросов
        self.conversation_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                QUESTION_1: [CallbackQueryHandler(self.handle_answer, pattern='^answer_.*$')],
                QUESTION_2: [CallbackQueryHandler(self.handle_answer, pattern='^answer_.*$')],
                QUESTION_3: [CallbackQueryHandler(self.handle_answer, pattern='^answer_.*$')],
                QUESTION_4: [CallbackQueryHandler(self.handle_answer, pattern='^answer_.*$')],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Приветственное сообщение и кнопки для старта теста
        keyboard = [
            [InlineKeyboardButton("Начать тест", callback_data='start_test')],
            # [InlineKeyboardButton("Мой ID", callback_data='get_id')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Добро пожаловать в авто-опросник! Нажмите на кнопку, чтобы начать.", reply_markup=reply_markup)
        return ConversationHandler.END

    async def start_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Начало теста: очистка старых данных и первый вопрос
        self.user_answers.clear()
        question_text, _ = QUESTIONS[0]
        await update.callback_query.message.edit_text(f"🎯 {question_text}")
        await self.send_buttons(update, 0)
        return QUESTION_1

    async def send_buttons(self, update: Update, question_index: int) -> None:
        # Отправка кнопок с вариантами ответов
        question_text, _ = QUESTIONS[question_index]
        options = ANSWER_OPTIONS[question_index]

        # Формируем кнопки для вариантов ответа
        keyboard = [
            [InlineKeyboardButton(option, callback_data=f"answer_{index}") for index, option in enumerate(options)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(f"🎯 {question_text}", reply_markup=reply_markup)

    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        query.answer()

        # Извлекаем индекс вопроса из callback_data (например, 'answer_0', 'answer_1' и т.д.)
        callback_data = query.data

        # Если это команда для старта теста
        if callback_data == 'start_test':
            return await self.start_test(update, context)

        # Если это команда для получения ID
        # elif callback_data == 'get_id':
        #     return await self.get_id(update, context)

        answer_index = callback_data.split('_')[-1]
        answer_index = int(answer_index)
        user_id = update.effective_user.id

        # Сохраняем ответ
        if user_id not in self.user_answers:
            self.user_answers[user_id] = []
        self.user_answers[user_id].append(ANSWER_OPTIONS[len(self.user_answers[user_id])][answer_index])

        # Переход к следующему вопросу
        if len(self.user_answers[user_id]) < len(QUESTIONS):
            await self.send_buttons(update, len(self.user_answers[user_id]))
            return len(self.user_answers[user_id])
        else:
            # Завершаем опрос и показываем результаты
            summary = "\n".join([f"{QUESTIONS[i][0]}: {self.user_answers[user_id][i]}" for i in range(len(QUESTIONS))])
            await query.edit_message_text(f"Спасибо за участие! Ваши ответы:\n{summary}")
            return ConversationHandler.END

    async def get_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Отправляем ID пользователя
        user_id = update.effective_user.id
        await update.callback_query.message.edit_text(f"Ваш ID: {user_id}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Опрос отменен.")
        return ConversationHandler.END

    def run(self):
        self.app.add_handler(self.conversation_handler)
        print("Бот запущен...")
        self.app.run_polling()


if __name__ == "__main__":
    bot = CarBot(TOKEN)
    bot.run()
