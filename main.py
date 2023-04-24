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
    mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
    result = mycursor.fetchmany(1)
    mycursor.execute(f'SELECT teleid FROM scores WHERE teleid = {message.chat.id}')
    result2 = mycursor.fetchmany(1)
    if not result:
        mycursor.execute(f"INSERT INTO just(teleid, which) VALUES({message.chat.id}, {random.randint(1, 2)})")
        mydb.commit()
    else:
        delete_queue(message.chat.id, result[0][0])
        user_name = message.from_user.username
        service = telebot.types.ReplyKeyboardMarkup(True, True)
        service.row('Поиск собеседника')
        bot.send_message(message.chat.id, f"Привет, {user_name}! Это анонимный чат бот. Нажмите кнопку ниже, чтоб начать поиск собеседника".format(message.from_user), reply_markup = service)
    if not result2:
        mycursor.execute(f"SELECT name FROM names WHERE teleid = {message.chat.id}")
        name = mycursor.fetchmany(1)
        mycursor.execute(f'INSERT INTO scores(teleid, name, score) VALUES({message.chat.id}, "{name[0][0]}", 0)')
        mydb.commit()

@bot.message_handler(commands=["addme"])
def start(message):
    mycursor.execute(f"SELECT name FROM names WHERE teleid = {message.chat.id}")
    result2 = mycursor.fetchmany(1)
    bot.send_message(message.chat.id, f'{result2}')
    # if not result:
    #     mycursor.execute(f"INSERT INTO just(teleid, which) VALUES({message.chat.id}, {random.randint(1, 2)})")
    if not result2:
        mycursor.execute(f"INSERT INTO names(teleid, name) VALUES({message.chat.id}, '{message.from_user.first_name}')")
        mydb.commit()
    # else:
        # delete_queue(message.chat.id, result[0][0])
        # user_name = message.from_user.username
        # service = telebot.types.ReplyKeyboardMarkup(True, True)
        # service.row('Поиск собеседника')
        # bot.send_message(message.chat.id, f"Привет, {user_name}! Это анонимный чат бот. Нажмите кнопку ниже, чтоб начать поиск собеседника".format(message.from_user), reply_markup = service)


@bot.message_handler(commands=["menu"])
def menu(message):
    service = telebot.types.ReplyKeyboardMarkup(True, True)
    service.row('Поиск собеседника')
    bot.send_message(message.chat.id, 'Меню'.format(message.from_user), reply_markup = service)

@bot.message_handler(commands=["stop"])
def stop(message):
    chat_info = get_active_chat(message.chat.id)
    if chat_info != False:
        delete_chat(chat_info[0])
        mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
        result = mycursor.fetchmany(1)
        service = telebot.types.ReplyKeyboardMarkup(True, True)
        service.row('Поиск собеседника')
        mycursor.execute(f"UPDATE scores SET score = score - 2 WHERE teleid = {message.chat.id}")
        mycursor.execute(f"UPDATE scores SET score = score + 2 WHERE teleid = {chat_info[1]}")
        mydb.commit()
        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {message.chat.id}")
        my_scores = mycursor.fetchmany(1)
        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {chat_info[1]}")
        his_scores = mycursor.fetchmany(1)
        bot.send_message(message.chat.id, f'Вы вышли из чатаи у вас {my_scores[0][0]} баллов', reply_markup = service)
        bot.send_message(chat_info[1], f'Собеседник покинул чати у вас {his_scores[0][0]} баллов', reply_markup = service)
        bot.send_message(message.chat.id, f'{result[0][0]}', reply_markup = service)
        changer(message.chat.id, result[0][0])
    else:
        bot.send_message(message.chat.id, 'Вы не создавали чат')

@bot.message_handler(content_types=["text", "photo"])
def bot_message(message):
    if message.chat.type == 'private':
        if message.text == 'Поиск собеседника':
            mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
            result = mycursor.fetchmany(1)
            service = telebot.types.ReplyKeyboardMarkup(True, True)
            service.row('Остановить поиск')
            chat_two = get_chat(result[0][0])
            if create_chat(message.chat.id, chat_two, result[0][0]) == False:
                add_queue(message.chat.id, result[0][0])
                bot.send_message(message.chat.id, 'Идет поиск', reply_markup = service)
            else:
                mess = f'Собеседник найден! Нажмите /stop чтоб закончить диалог'
                service = telebot.types.ReplyKeyboardMarkup(True, True)
                service.row('/stop')
                bot.send_message(message.chat.id, mess, reply_markup = service)
                bot.send_message(chat_two, mess, reply_markup = service)
        elif message.text == 'Остановить поиск':
            mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
            result = mycursor.fetchmany(1)
            delete_queue(message.chat.id, result[0][0])
            bot.send_message(message.chat.id, 'Поиск остановлен! Нажмите /menu')
        elif message.content_type == "photo":
            raw = message.photo[2].file_id
            name = raw+".jpg"
            file_info = bot.get_file(raw)
            downloaded_file = bot.download_file(file_info.file_path)
            with open(name,'wb') as new_file:
                new_file.write(downloaded_file)
            img = open(name, 'rb')
            chat_info = get_active_chat(message.chat.id)
            bot.send_photo(chat_info[1], img)
        elif message.text[:1] == '-':
            mycursor.execute(f'SELECT teleid FROM names WHERE name = "{message.text[1:]}"')
            result = mycursor.fetchmany(1)
            if not result:
                bot.send_message(message.chat.id, 'такого игрока нет')
            else:
                chat_info = get_active_chat(message.chat.id)
                if result[0][0] == chat_info[1]:
                    chat_info = get_active_chat(message.chat.id)
                    if chat_info != False:
                        delete_chat(chat_info[0])
                        mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
                        result = mycursor.fetchmany(1)
                        service = telebot.types.ReplyKeyboardMarkup(True, True)
                        service.row('Поиск собеседника')
                        mycursor.execute(f"UPDATE scores SET score = score + 3 WHERE teleid = {message.chat.id}")
                        mydb.commit()
                        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {message.chat.id}")
                        my_scores = mycursor.fetchmany(1)
                        bot.send_message(message.chat.id, f'Ты угадал!!! У тебя {my_scores[0][0]} баллов', reply_markup = service)
                        mycursor.execute(f"SELECT name FROM names WHERE teleid = {message.chat.id}")
                        person = mycursor.fetchmany(1)
                        mycursor.execute(f"SELECT name FROM names WHERE teleid = {chat_info[1]}")
                        ideareally = mycursor.fetchmany(1)
                        mycursor.execute(f'INSERT INTO guesses(teleid, person, idea, really) VALUES({message.chat.id}, "{person[0][0]}", "{ideareally[0][0]}", "{ideareally[0][0]}")')
                        mydb.commit()
                        mycursor.execute(f"UPDATE scores SET score = score - 1 WHERE teleid = {chat_info[1]}")
                        mydb.commit()
                        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {chat_info[1]}")
                        his_scores = mycursor.fetchmany(1)
                        bot.send_message(chat_info[1], f'Собеседник узнал вас, у тебя {his_scores[0][0]} баллов', reply_markup = service)
                        changer(message.chat.id, result[0][0])
                else:
                    if chat_info != False:
                        delete_chat(chat_info[0])
                        mycursor.execute(f"SELECT which FROM just WHERE teleid = {message.chat.id}")
                        result = mycursor.fetchmany(1)
                        service = telebot.types.ReplyKeyboardMarkup(True, True)
                        service.row('Поиск собеседника')
                        mycursor.execute(f"UPDATE scores SET score = score - 1 WHERE teleid = {message.chat.id}")
                        mydb.commit()
                        mycursor.execute(f"UPDATE scores SET score = score + 1 WHERE teleid = {chat_info[1]}")
                        mydb.commit()
                        mycursor.execute(f"SELECT name FROM names WHERE teleid = {message.chat.id}")
                        person = mycursor.fetchmany(1)
                        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {chat_info[1]}")
                        his_scores = mycursor.fetchmany(1)
                        mycursor.execute(f"SELECT score FROM scores WHERE teleid = {message.chat.id}")
                        my_scores = mycursor.fetchmany(1)
                        mycursor.execute(f"SELECT name FROM names WHERE teleid = {chat_info[1]}")
                        really = mycursor.fetchmany(1)
                        mycursor.execute(f'INSERT INTO guesses(teleid, person, idea, really) VALUES({message.chat.id}, "{person[0][0]}", "{message.text[1:]}", "{really[0][0]}")')
                        mydb.commit()
                        bot.send_message(message.chat.id, f'Ты не угадал!!! У тебя {my_scores[0][0]} баллов', reply_markup = service)
                        bot.send_message(chat_info[1], f'Собеседник не узнал вас, у тебя {his_scores[0][0]} баллов', reply_markup = service)
                        changer(message.chat.id, result[0][0])
        else:
            chat_info = get_active_chat(message.chat.id)
            bot.send_message(chat_info[1], message.text)


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