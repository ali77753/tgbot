import telebot
from telebot import types

# Замените на свой токен
TOKEN = '8505440498:AAHQybT8Xykt90fEac-9sreBQlJLziCYDmM'

bot = telebot.TeleBot(TOKEN)

# Хранилище данных пользователей: {chat_id: {'state': 'waiting_income', 'income': None}}
user_data = {}

# Ставки налогов: ключ для callback, текст кнопки, процент
TAX_RATES = {
    'usn_6': ('УСН Доходы (6%)', 0.06),
    'usn_15': ('УСН Доходы минус расходы (15%)', 0.15),
    'npd_4': ('НПД (самозанятый, 4%)', 0.04),
    'npd_6': ('НПД (самозанятый, 6%)', 0.06),
}


# ------------------- Команда /start -------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    # Сбрасываем состояние пользователя
    user_data[chat_id] = {'state': 'idle', 'income': None}

    # Создаём Reply-кнопку "Ввести доход"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    item = types.KeyboardButton('💰 Ввести доход')
    markup.add(item)

    bot.send_message(
        chat_id,
        "Привет! Я помогу рассчитать налог для ИП или самозанятого.\n"
        "Нажми кнопку ниже, чтобы начать.",
        reply_markup=markup
    )


# ------------------- Обработка текстовых сообщений -------------------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text.strip()

    # ЕСЛИ ПОЛЬЗОВАТЕЛЬ НАЖАЛ "🔄 НОВЫЙ РАСЧЁТ"
    if text == '🔄 Новый расчёт':
        # Сбрасываем состояние и показываем кнопку "Ввести доход"
        user_data[chat_id] = {'state': 'idle', 'income': None}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        item = types.KeyboardButton('💰 Ввести доход')
        markup.add(item)
        bot.send_message(
            chat_id,
            "Нажмите кнопку ниже, чтобы ввести новый доход:",
            reply_markup=markup
        )
        return

    # Если пользователь нажал кнопку "💰 Ввести доход"
    if text == '💰 Ввести доход':
        # Устанавливаем состояние ожидания ввода дохода
        user_data[chat_id] = {'state': 'waiting_income', 'income': None}
        # Убираем Reply-кнопки, просим ввести число
        markup_remove = types.ReplyKeyboardRemove()
        bot.send_message(
            chat_id,
            "Введите сумму дохода в рублях (только число):",
            reply_markup=markup_remove
        )
        return

    # Проверяем состояние пользователя
    state = user_data.get(chat_id, {}).get('state')

    if state == 'waiting_income':
        # Пытаемся преобразовать ввод в число
        try:
            income = float(text.replace(',', '.'))
            if income < 0:
                raise ValueError("Доход не может быть отрицательным")
            # Сохраняем доход и меняем состояние на ожидание выбора налога
            user_data[chat_id] = {'state': 'waiting_tax', 'income': income}

            # Показываем Inline-кнопки с вариантами налогов
            markup_inline = types.InlineKeyboardMarkup(row_width=2)
            for key, (label, _) in TAX_RATES.items():
                btn = types.InlineKeyboardButton(label, callback_data=key)
                markup_inline.add(btn)

            bot.send_message(
                chat_id,
                f"Доход: {income:.2f} руб.\nТеперь выберите категорию налога:",
                reply_markup=markup_inline
            )
        except ValueError:
            bot.send_message(chat_id, "Пожалуйста, введите корректное число (например, 50000 или 12500.50).")
    else:
        # Если состояние не определено или idle, предлагаем начать с /start
        bot.send_message(
            chat_id,
            "Не понимаю команду. Нажмите /start для начала работы."
        )


# ------------------- Обработка нажатий на Inline-кнопки -------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    data = call.data

    # Получаем данные пользователя
    user_info = user_data.get(chat_id)
    if not user_info or user_info['state'] != 'waiting_tax' or user_info['income'] is None:
        bot.answer_callback_query(call.id, "Сначала введите доход!")
        return

    income = user_info['income']
    if data in TAX_RATES:
        label, rate = TAX_RATES[data]
        tax = income * rate
        # Формируем ответ
        response = (
            f"💰 Доход: {income:.2f} руб.\n"
            f"📊 Категория: {label}\n"
            f"🧾 Ставка: {rate * 100:.0f}%\n"
            f"✅ Сумма налога: {tax:.2f} руб."
        )
        # Редактируем сообщение с кнопками, убираем их (чтобы нельзя было нажать повторно)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=response
        )
        # Сбрасываем состояние и предлагаем начать заново (Reply-кнопка)
        user_data[chat_id] = {'state': 'idle', 'income': None}

        # Добавляем кнопку "🔄 Новый расчёт"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton('🔄 Новый расчёт'))
        bot.send_message(
            chat_id,
            "Хотите рассчитать ещё? Нажмите кнопку ниже.",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "Неизвестная категория")


# ------------------- Запуск бота -------------------
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()