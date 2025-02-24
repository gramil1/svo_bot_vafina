import telebot
from telebot import types
import sqlite3
import requests  

BOT_TOKEN = 'Ваш токен'

bot = telebot.TeleBot(BOT_TOKEN)


DATABASE_NAME = 'karima_bot.db'

def create_table():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            phone_number TEXT,
            email_address TEXT,
            location TEXT,
            needs_consultation INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

create_table()

user_data = {}  

STATES = {
    'START': 0,
    'FULL_NAME': 1,
    'PHONE_NUMBER': 2,
    'EMAIL_ADDRESS': 3,
    'LOCATION': 4,
    'CONSULTATION': 5,
    'CONFIRM': 6
}

def get_user_state(user_id):
    if user_id not in user_data:
        user_data[user_id] = {'state': STATES['START']}
    return user_data[user_id]['state']

def update_user_state(user_id, state):
    user_data[user_id]['state'] = state


def save_request_to_db(full_name, phone_number, email_address, location, needs_consultation):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO requests (full_name, phone_number, email_address, location, needs_consultation)
        VALUES (?, ?, ?, ?, ?)
    """, (full_name, phone_number, email_address, location, needs_consultation))
    conn.commit()
    conn.close()
    print("Заявка успешно сохранена в базу данных!")


def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return(pattern, email) is not None

def validate_phone_number(phone):
    pattern = r"^\+?[0-9]{10,15}$"  
    return(pattern, phone) is not None


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_data[user_id] = {} # Очищаем данные пользователя при старте
    update_user_state(user_id, STATES['START'])
    bot.send_message(message.chat.id, "Здравствуйте! Я бот для приема заявок на ремонт компьютеров.\nПожалуйста, заполните форму, чтобы мы могли вам помочь.\n\nВведите ваше ФИО:")
    update_user_state(message.from_user.id, STATES['FULL_NAME'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['FULL_NAME'])
def get_full_name(message):
    user_id = message.from_user.id
    user_data[user_id]['full_name'] = message.text
    bot.send_message(message.chat.id, "Отлично! Теперь введите ваш номер телефона для связи:")
    update_user_state(user_id, STATES['PHONE_NUMBER'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['PHONE_NUMBER'])
def get_phone_number(message):
    user_id = message.from_user.id
    phone_number = message.text
    if not validate_phone_number(phone_number):
        bot.send_message(message.chat.id, "Неверный формат номера телефона. Пожалуйста, введите номер в формате +79123456789 или 89123456789:")
        return
    user_data[user_id]['phone_number'] = phone_number
    bot.send_message(message.chat.id, "Прекрасно! Теперь введите ваш email адрес:")
    update_user_state(user_id, STATES['EMAIL_ADDRESS'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['EMAIL_ADDRESS'])
def get_email_address(message):
    user_id = message.from_user.id
    email_address = message.text
    if not validate_email(email_address):
        bot.send_message(message.chat.id, "Неверный формат email. Пожалуйста, введите корректный email адрес:")
        return
    user_data[user_id]['email_address'] = email_address
    bot.send_message(message.chat.id, "Отлично! Теперь укажите местонахождение (адрес) для выезда мастера:")
    update_user_state(user_id, STATES['LOCATION'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['LOCATION'])
def get_location(message):
    user_id = message.from_user.id
    user_data[user_id]['location'] = message.text

    # --- Нужна консультация? ---
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Да', 'Нет')

    bot.send_message(message.chat.id, "Вам требуется консультация специалиста?", reply_markup=markup)
    update_user_state(user_id, STATES['CONSULTATION'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['CONSULTATION'])
def get_consultation(message):
    user_id = message.from_user.id
    if message.text == 'Да':
        user_data[user_id]['needs_consultation'] = 1
    else:
        user_data[user_id]['needs_consultation'] = 0

    # --- Подтверждение данных ---
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Подтвердить', 'Отменить')

    bot.send_message(message.chat.id, f"Пожалуйста, проверьте введенные данные:\n\n"
                                      f"ФИО: {user_data[user_id]['full_name']}\n"
                                      f"Телефон: {user_data[user_id]['phone_number']}\n"
                                      f"Email: {user_data[user_id]['email_address']}\n"
                                      f"Адрес: {user_data[user_id]['location']}\n"
                                      f"Требуется консультация: {'Да' if user_data[user_id]['needs_consultation'] == 1 else 'Нет'}\n\n"
                                      f"Все верно?", reply_markup=markup)

    update_user_state(user_id, STATES['CONFIRM'])


@bot.message_handler(func=lambda message: get_user_state(message.from_user.id) == STATES['CONFIRM'])
def confirm_data(message):
    user_id = message.from_user.id
    if message.text == 'Подтвердить':
        # Сохраняем данные в базу данных
        save_request_to_db(user_data[user_id]['full_name'],
                           user_data[user_id]['phone_number'],
                           user_data[user_id]['email_address'],
                           user_data[user_id]['location'],
                           user_data[user_id]['needs_consultation'])

        bot.send_message(message.chat.id, "Спасибо за вашу заявку!  Мы свяжемся с вами в ближайшее время.", reply_markup=types.ReplyKeyboardRemove())
    elif message.text == 'Отменить':
        bot.send_message(message.chat.id, "Заявка отменена.  Вы можете начать заново командой /start.", reply_markup=types.ReplyKeyboardRemove())
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выберите 'Подтвердить' или 'Отменить'.", reply_markup=types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add('Подтвердить', 'Отменить'))

    
    update_user_state(user_id, STATES['START'])
    user_data[user_id] = {}


# --- Запуск бота ---
if __name__ == '__main__':
    bot.polling(none_stop=True)
