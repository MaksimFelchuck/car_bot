from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
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
from crm import AmoCrmFetcher
import re
from pathlib import Path
import asyncio

TOKEN = os.environ["TOKEN"]


class Pipline:
    target_pipline = 8868612  # (, "ЦЕЛЕВАЯ ЗАЯВКА")
    tresh_pipline = 8868609  # (, "ОТСТОЙНИК")


PIPLINE_ID = 2776459


custom_fields = {
    0: {
        "field_id": 724001,
        "enum_ids": {
            "до 1,5 млн": 1464257,
            "1,5-3 млн": 1464259,
            "3-5 млн": 1464261,
            "более 5 млн": 1464263,
        },
    },
    1: {
        "field_id": 723997,
        "enum_ids": {
            "до 10 дней": 1464249,
            "до 1 мес": 1464251,
            "до 2х мес": 1464253,
            "до 6 мес": 1464255,
        },
    },
    2: {
        "field_id": 724003,
        "enum_ids": {
            "Да": 1464265,
            "Нет": 1464267,
        },
    },
    3: {
        "field_id": 724005,
        "enum_ids": {
            "Корейские": 1464269,
            "Европейские": 1464271,
            "Американские": 1464273,
        },
    },
    4: {
        "field_id": 724007,
        "enum_ids": {
            "ЦФО": 1464275,
            "Сибирь": 1464277,
            "ДВ": 1464279,
        },
    },
    5: {
        "field_id": 724009,
        "enum_ids": {
            "TG": 1464281,
            "Whatsapp": 1464283,
            "Телефон": 1464285,
        },
    },
}


def validate_phone(phone: str) -> bool:
    pattern = re.compile(r"^(?:\+7|8)\d{10}$")
    return bool(pattern.match(phone))


(
    QUESTION_1,
    QUESTION_2,
    QUESTION_3,
    QUESTION_4,
    QUESTION_5,
    QUESTION_6,
    WAIT_PHONE,
    RESULT,
) = range(8)

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
        self.completed_surveys = set()  # Множество пользователей, завершивших опрос
        self.crm = AmoCrmFetcher()

        # Разворачиваем ConversationHandler для вопросов
        self.conversation_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                MessageHandler(
                    filters.Regex("^/start$"), self.start
                ),  # на всякий случай
                CallbackQueryHandler(self.start_test, pattern="^start_test$"),
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
        self.app.add_handlers([self.conversation_handler])

    async def show_welcome_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Показывает приветственное сообщение с картинкой и кнопкой начала теста"""
        keyboard = [
            [InlineKeyboardButton("Начать тест", callback_data="start_test")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        image_path = Path("photo/car.jpg")
        photo = str(image_path)

        # Отправка фото
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=photo,
        )

        # Отправка приветственного сообщения с кнопкой
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Добро пожаловать в авто-опросник!\nЧтобы лучшим образом подобрать для вас автомобиль из Южной Кореи, пожалуйста ответьте на 6 коротких вопросов.\nЧтобы начать, нажмите 'Начать тест' в диалоговом окне.",
                reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                "Добро пожаловать в авто-опросник!\nЧтобы лучшим образом подобрать для вас автомобиль из Южной Кореи, пожалуйста ответьте на 6 коротких вопросов.\nЧтобы начать, нажмите 'Начать тест' в диалоговом окне.",
                reply_markup=reply_markup,
            )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.chat_data.clear()
        user_id = update.effective_user.id

        # Проверяем, завершил ли пользователь опрос ранее
        if user_id in self.completed_surveys:
            await update.message.reply_text(
                "Вы уже завершили опрос. Наш специалист свяжется с вами в ближайшее время."
            )
            return ConversationHandler.END

        if user_id in self.user_answers:
            if len(self.user_answers[user_id]) < len(QUESTIONS):
                pass
            else:
                # Здесь можно отправить данные в CRM
                await update.message.reply_text(
                    f"Спасибо, что прошли опрос, наш специалист свяжется с вами!"
                )
                return ConversationHandler.END
        # Показываем приветственное сообщение
        await self.show_welcome_message(update, context)
        return ConversationHandler.END

    async def start_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> int:
        # Начало теста: очистка старых данных и первый вопрос
        user_id = update.effective_user.id

        # Проверяем, завершил ли пользователь опрос ранее
        if user_id in self.completed_surveys:
            await update.callback_query.message.edit_text(
                "Вы уже завершили опрос. Наш специалист свяжется с вами в ближайшее время."
            )
            return ConversationHandler.END

        # Очищаем старые ответы пользователя
        if user_id in self.user_answers:
            del self.user_answers[user_id]

        question_text, _ = QUESTIONS[0]
        await update.callback_query.message.edit_text(f"🎯 {question_text}")
        await self.send_buttons(update, 0)
        return QUESTION_1

    def chunk_options(self, options, chunk_size=3):
        """Разделяет список вариантов на несколько подсписков по chunk_size"""
        return [options[i : i + chunk_size] for i in range(0, len(options), chunk_size)]

    async def send_buttons(self, update: Update, question_index: int) -> None:
        question_text, _ = QUESTIONS[question_index]
        options = ANSWER_OPTIONS[question_index]

        # Формируем кнопки с правильными callback_data
        keyboard = []
        for idx, option in enumerate(options):
            row = idx // 3  # 3 кнопки в строке
            if len(keyboard) <= row:
                keyboard.append([])
            keyboard[row].append(
                InlineKeyboardButton(option, callback_data=f"answer_{idx}")
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            f"🎯 {question_text}", reply_markup=reply_markup
        )

    async def handle_answer(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        msg = "Произошла ошибка. Пожалуйста, нажмите /start что бы попробовать ещё раз."
        try:
            query = update.callback_query
            await query.answer()

            # Извлекаем индекс вопроса из callback_data (например, 'answer_0', 'answer_1' и т.д.)
            callback_data = query.data

            user_id = update.effective_user.id

            # Если это команда для старта теста
            if callback_data == "start_test":

                return await self.start_test(update, context)

            answer_index = callback_data.split("_")[-1]
            answer_index = int(answer_index)

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
                    "📱Введите номер телефона в формате (+79998887766):"
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
        ans = self.user_answers.get(user_id)
        if not ans:
            print(f"Не нашлось ответов для {user_id=}")
            await update.message.reply_text(
                "Не получилось сохранить ответы, пожалуйста нажмите /start для повторного прохождения опроса."
            )
            return ConversationHandler.END
        if validate_phone(phone):
            if all([ans[i] in GOOD_QUESTION_LIST for i in range(len(QUESTIONS))]):
                status_id = Pipline.target_pipline
            else:
                status_id = Pipline.tresh_pipline
            custom_fields_data = [
                {
                    "field_id": custom_fields[i]["field_id"],
                    "values": [
                        {
                            "enum_id": custom_fields[i]["enum_ids"][
                                self.user_answers[user_id][i]
                            ]
                        }
                    ],
                }
                for i in range(len(QUESTIONS))
            ]
            custom_fields_data.append(
                {
                    "field_id": 724011,
                    "values": [{"value": phone}],
                }
            )
            # Здесь можно отправить данные в CRM
            await update.message.reply_text(
                """Отлично! 

Подпишитесь на мой канал (https://t.me/scanauto_korea) и я начну подбор машины для вас. 
В канале я оперативно публикую все новости по поставкам и самые свежие предложения."""
            )
            # Отправляем лида в срм
            await self.crm.create_lead_full(
                name="",
                pipeline_id=PIPLINE_ID,
                status_id=status_id,
                # price=5_000_000,
                custom_fields=custom_fields_data,  #: dict[int, Union[str, int, list[str]]]
            )
            # Добавляем пользователя в множество завершённых опросов
            self.completed_surveys.add(user_id)
            # Удаляем ответы пользователя после успешной отправки в CRM
            if user_id in self.user_answers:
                del self.user_answers[user_id]
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "❌ Неверный формат номера. Попробуйте ещё раз:"
            )
            return WAIT_PHONE

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        # Если пользователь уже завершил опрос, не позволяем отменить
        if user_id in self.completed_surveys:
            await update.message.reply_text(
                "Вы уже завершили опрос. Наш специалист свяжется с вами в ближайшее время."
            )
            return ConversationHandler.END
        await update.message.reply_text("Опрос отменен.")
        if user_id in self.user_answers:
            self.user_answers.pop(user_id)
        return ConversationHandler.END

    def run(self):
        self.app.add_handler(self.conversation_handler)
        # Установка меню команд через стандартный event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            self.app.bot.set_my_commands([
                BotCommand("start", "Запустить бота"),
                BotCommand("cancel", "Отменить опрос"),
            ])
        )
        print("Бот запущен...")
        self.app.run_polling()


if __name__ == "__main__":
    bot = CarBot(TOKEN)
    bot.run()
