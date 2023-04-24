import os
import telebot
import logging
import random
import mysql.connector
from telebot import types
from config import *
from flask import Flask, request


bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)

mydb = mysql.connector.connect(
    host = os.environ.get('MYSQLHOST'),
    port = os.environ.get('MYSQLPORT'),
    user = os.environ.get('MYSQLUSER'),
    password = os.environ.get('MYSQLPASSWORD'),
    database = os.environ.get('MYSQLDATABASE')
)
mycursor = mydb.cursor()

@bot.message_handler(commands=["start"])
def start(message):
    service = telebot.types.ReplyKeyboardMarkup(True, True)
    service.row('Войти')
    user_name = message.from_user.username
    msg = f"Привет, {user_name}! Это NIS Assistant чат бот. \n Нажмите Войти чтобы войти "
    bot.send_message(message.chat.id, msg.format(message.from_user), reply_markup = service)
    

@bot.message_handler(content_types=["text", "photo"])
def bot_message(message):
    if message.chat.type == 'private':
        if message.text == 'Войти':
            msg = bot.send_message(message.chat.id, 'Введите email')
            bot.register_next_step_handler(msg, check)
        elif message.content_type == "photo":
            raw = message.photo[2].file_id
            name = raw+".jpg"
            file_info = bot.get_file(raw)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(name,'wb') as new_file:
                new_file.write(downloaded_file)
            img = open(name, 'rb')

def check(message):
    global semail
    semail = message.text.lower()
    mycursor.execute(f"SELECT email FROM students WHERE email = %s",(semail,))
    result = mycursor.fetchone()
    bot.send_message(message.chat.id, f'{result}')
    if result:
        mycursor.execute(f"SELECT teleid FROM students WHERE email = %s",(semail,))
        dbresult = mycursor.fetchone()
        if not dbresult[0]:
            msg = bot.send_message(message.chat.id, 'Введите пароль')
            bot.register_next_step_handler(msg, check_pass)
        elif int(dbresult[0]) == message.chat.id:
            global student_name
            mycursor.execute(f"SELECT name FROM students WHERE email = %s",(semail,))
            student_name = mycursor.fetchone()
            service = telebot.types.ReplyKeyboardMarkup(True, False)
            service.row('Мои результаты', 'Расписание')
            msg = bot.send_message(message.chat.id, f'{student_name[0]}, вы спешно вошли', reply_markup = service)
            bot.register_next_step_handler(msg, student_main)
        else:
            bot.send_message(message.chat.id, 'В доступе отказано')
            start(message)
    else:
        bot.send_message(message.chat.id, 'Ученик с таким email не найден')
        start(message)

def check_pass(message):
    mycursor.execute(f"SELECT password FROM students WHERE email = %s",(semail,))
    result = mycursor.fetchone()
    if message.text == result[0]:
        global student_name
        mycursor.execute(f"SELECT name FROM students WHERE email = %s",(semail,))
        student_name = mycursor.fetchone()
        mycursor.execute(f"UPDATE students SET teleid = {message.chat.id} WHERE email = %s",(semail,))
        mydb.commit()
        mycursor.execute(f"UPDATE results SET teleid = {message.chat.id} WHERE email = %s",(semail,))
        mydb.commit()
        service = telebot.types.ReplyKeyboardMarkup(True, False)
        service.row('Мои результаты', 'Расписание')
        msg = bot.send_message(message.chat.id, f'{student_name[0]}, вы спешно вошли', reply_markup = service)
        bot.register_next_step_handler(msg, student_main)
    else:
        bot.send_message(message.chat.id, 'Не правильный пароль')
        start(message)

def student_main(message):
    if message.text == 'Расписание':
        mycursor.execute(f"SELECT class FROM students WHERE teleid = %s",(message.chat.id,))
        result = mycursor.fetchone()
        img = 'sources/'+result[0]+'.png'
        bot.send_photo(message.chat.id, photo=open(img, 'rb'))
        student_main(message)
    if message.text == 'Мои результаты':
        mycursor.execute(f"SELECT score FROM students WHERE teleid = %s",(message.chat.id,))
        result = mycursor.fetchone()
        bot.send_photo(message.chat.id, f"Вы набрали {result} баллов на тестировании")
        student_main(message)


@server.route(f"/{BOT_TOKEN}", methods=["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))