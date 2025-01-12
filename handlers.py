import logging
import sql_def
import questions

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Замените "YOUR_BOT_TOKEN" на токен, который вы получили от BotFather
API_TOKEN = '7337687477:AAFfCSwm3I2g1F-Iqus0v0a3m2wp25hfQZw'


# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем в сборщик одну кнопку
    builder.add(types.KeyboardButton(text="Начать игру"))
    # Прикрепляем кнопки к сообщению
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

# Хэндлер на команды /quiz
@dp.message(F.text=="Начать игру")
@dp.message(F.text=="Начать новую игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз!", reply_markup=types.ReplyKeyboardRemove())
    # Запускаем новый квиз
    await new_quiz(message)

async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    username = message.from_user.username
    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    current_score = 0
    await sql_def.update_quiz_index(user_id, username, current_question_index, current_score)

    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)

async def get_question(message, user_id):

    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await sql_def.get_quiz_index(user_id)
    # Получаем индекс правильного ответа для текущего вопроса
    correct_index = questions.quiz_data[current_question_index]['correct_option']
    # Получаем список вариантов ответа для текущего вопроса
    opts = questions.quiz_data[current_question_index]['options']

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts, opts[correct_index])
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(f"{questions.quiz_data[current_question_index]['question']}", reply_markup=kb)

def generate_options_keyboard(answer_options, right_answer):
  # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем 4 Inline кнопки, а точнее Callback-кнопки
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            # Если ответ верный сформируется колбэк-запрос с данными 'right_answer'
            # Если ответ неверный сформируется колбэк-запрос с данными 'wrong_answer'
            callback_data=f"right_answer {option}" if option == right_answer else f"wrong_answer {option}")
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()

@dp.callback_query(F.data.contains("right_answer"))
async def right_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса для данного пользователя
    current_question_index = await sql_def.get_quiz_index(callback.from_user.id)
    current_score = await sql_def.get_quiz_score(callback.from_user.id)
    option = callback.data[13:]
    # Отправляем в чат сообщение, что ответ верный
    await callback.message.answer(f"Ваш ответ {option}. Верно!")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    current_score += 1
    await sql_def.update_quiz_index(callback.from_user.id, callback.from_user.username, current_question_index, current_score)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(questions.quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        builder = ReplyKeyboardBuilder()
        kb = [
            [
                types.KeyboardButton(text="Начать новую игру"),
                types.KeyboardButton(text="Статистика")
            ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True
        )
        builder.add(types.KeyboardButton(text="Начать новую игру"))
        await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Правильных ответов: {current_score}", reply_markup=keyboard)
        

@dp.callback_query(F.data.contains("wrong_answer"))
async def wrong_answer(callback: types.CallbackQuery):
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    # Получение текущего вопроса для данного пользователя
    current_question_index = await sql_def.get_quiz_index(callback.from_user.id)
    current_score = await sql_def.get_quiz_score(callback.from_user.id)
    option = callback.data[13:]
    correct_option = questions.quiz_data[current_question_index]['correct_option']

    # Отправляем в чат сообщение об ошибке с указанием верного ответа
    await callback.message.answer(f"Ваш ответ {option}. Неправильно. Правильный ответ: {questions.quiz_data[current_question_index]['options'][correct_option]}")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await sql_def.update_quiz_index(callback.from_user.id, callback.from_user.username, current_question_index, current_score)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(questions.quiz_data):
        # Следующий вопрос
        await get_question(callback.message, callback.from_user.id)
    else:
        # Уведомление об окончании квиза
        builder = ReplyKeyboardBuilder()
        kb = [
            [
                types.KeyboardButton(text="Начать новую игру"),
                types.KeyboardButton(text="Статистика")
            ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True
        )
        builder.add(types.KeyboardButton(text="Начать новую игру"))
        await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Правильных ответов: {current_score}", reply_markup=keyboard)

@dp.message(F.text=="Статистика")
async def stat_quiz(message: types.Message):
    all_stat = await sql_def.get_stat()
    content = []
    for stats in all_stat:
        content.append(f"Никнейм {stats[1]}, Текущий вопрос {stats[2]}, Правильных ответов {stats[3]}")
    await message.answer(f"{content}")