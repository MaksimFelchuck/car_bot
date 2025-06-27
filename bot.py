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
import httpx

TOKEN = os.environ["TOKEN"]
import re


def validate_phone(phone: str) -> bool:
    pattern = re.compile(r"^(?:\+7|8)\d{10}$")
    return bool(pattern.match(phone))



QUESTION_1, QUESTION_2, QUESTION_3, QUESTION_4, QUESTION_5, QUESTION_6, WAIT_PHONE, RESULT = range(8)

# Описание вопросов и ключевых значений
QUESTIONS = [
    ("Какой у вас бюджет на покупку автомобиля?", "budget"),
    ("Когда для вас актуальна покупка автомобиля?", "time_limit"),
    ("Требуется ли вам продать свой автомобиль для покупки нового?", "sell_auto"),
    ("Марки какой страны вы рассматриваете?", "mark"),
    ("В какой регион потребуется отправка авто?", "region"),
    ("Как с вами связаться?", "contact"),
    # ("Вы предпочитаете седан, хэтчбек, внедорожник или кроссовер?", "body_type"),
    # ("Выбираете автомат или механику?", "transmission"),
    # ("Рассматриваете только новые машины или подойдут и б/у?", "condition"),
]

# Варианты ответов для каждого вопроса
ANSWER_OPTIONS = {
    0: [
        "до 1,5 млн",
        "1,5-3 млн",  # da
        "3-5 млн",  # da
        "более 5 млн",  # da
    ],
    1: [
        "до 10 дней",  # da
        "до 1 мес",  # da
        "до 2х мес",
        "до 6 мес",
    ],
    2: [
        "Да",
        "Нет",  # da
    ],
    3: [
        "Корейские",  # da
        "Европейские",  # da
        "Американские",  # da
    ],
    4: [
        "ЦФО",  # da
        "Сибирь",  # da
        "ДВ",  # da
    ],
    5: [
        "TG",  # da
        "Whatsapp",  # da
        "Телефон",  # da
    ],
}
GOOD_QUESTION_LIST = [
    "1,5-3 млн",  # da
    "3-5 млн",  # da
    "более 5 млн",  # da
    "до 10 дней",  # da
    "до 1 мес",  # da
    "Нет",  # da
    "Корейские",  # da
    "Европейские",  # da
    "Американские",  # da
    "ЦФО",  # da
    "Сибирь",  # da
    "ДВ",  # da
    "TG",  # da
    "Whatsapp",  # da
    "Телефон",  # da
]


class CarBot:
    def __init__(self, token: str):
        self.app = ApplicationBuilder().token(token).build()
        self.user_answers = {}


        # Разворачиваем ConversationHandler для вопросов
        self.conversation_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                CallbackQueryHandler(self.handle_answer, pattern="^start_test$")
            ],
            states={
                QUESTION_1: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                QUESTION_2: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                QUESTION_3: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                QUESTION_4: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                QUESTION_5: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                QUESTION_6: [
                    CallbackQueryHandler(self.handle_answer, pattern="^answer_.*$")
                ],
                WAIT_PHONE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_phone)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
        self.app.add_handler(self.conversation_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Приветственное сообщение и кнопки для старта теста
        keyboard = [
            [InlineKeyboardButton("Начать тест", callback_data="start_test")],
            # [InlineKeyboardButton("Мой ID", callback_data='get_id')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Добро пожаловать в авто-опросник! Нажмите на кнопку, чтобы начать.",
            reply_markup=reply_markup,
        )
        return ConversationHandler.END

    async def start_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> int:
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
            [
                InlineKeyboardButton(option, callback_data=f"answer_{index}")
                for index, option in enumerate(options)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            f"🎯 {question_text}", reply_markup=reply_markup
        )

    async def handle_answer(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        msg = "Произошла ошибка. Пожалуйста, попробуйте позже."
        try:
            query = update.callback_query
            await query.answer()

            # Извлекаем индекс вопроса из callback_data (например, 'answer_0', 'answer_1' и т.д.)
            callback_data = query.data

            # Если это команда для старта теста
            if callback_data == "start_test":
                return await self.start_test(update, context)

            # Если это команда для получения ID
            # elif callback_data == 'get_id':
            #     return await self.get_id(update, context)

            answer_index = callback_data.split("_")[-1]
            answer_index = int(answer_index)
            user_id = update.effective_user.id

            # Сохраняем ответ
            if user_id not in self.user_answers:
                self.user_answers[user_id] = []
            self.user_answers[user_id].append(
                ANSWER_OPTIONS[len(self.user_answers[user_id])][answer_index]
            )

            # Переход к следующему вопросу
            if len(self.user_answers[user_id]) < len(QUESTIONS):
                await self.send_buttons(update, len(self.user_answers[user_id]))
                return len(self.user_answers[user_id])
            else:

                await query.edit_message_text(
                    "📱Введите номер телефона в формате +79998887766:"
                )
                return WAIT_PHONE  # ⬅ Переход к ожиданию номера
        except httpx.NetworkError as e:
            # Обработка сетевой ошибки
            print(f"Сетевая ошибка: {e}")
            await update.callback_query.message.reply_text(msg)
            return ConversationHandler.END
        except Exception as e:
            # Логируем другие ошибки
            print(f"Неизвестная ошибка: {e}")
            await update.callback_query.message.reply_text(msg)
            return ConversationHandler.END

    async def save_phone(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        phone = update.message.text.strip()
        user_id = update.effective_user.id

        if validate_phone(phone):
            if all(
                [
                    self.user_answers[user_id][i] in GOOD_QUESTION_LIST
                    for i in range(len(QUESTIONS))
                ]
            ):
                otstoinik = f"ОТСТОЙНИК!"

            else:
                otstoinik = f"РАБОТАЕМ!"

            # Здесь можно отправить данные в CRM
            await update.message.reply_text(
                f"Спасибо! Наш специалист свяжется с вами в ближайшее время. {otstoinik}\n[CRM] Данные пользователя {user_id}: {self.user_answers.get(user_id)} | Телефон: {phone}"
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Неверный формат номера. Попробуйте ещё раз:"
            )
            return WAIT_PHONE

    async def send_to_crm(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await update.callback_query.message.edit_text(
            "Тут я отправляю в срм запрос, нужно реализовать..."
        )

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
