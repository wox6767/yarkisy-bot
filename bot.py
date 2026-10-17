import os
import base64
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot

# Твой токен и ID группы (с минусом для корректной работы в чате)
TOKEN = "8693716546:AAFxJHGECP0tJQO5MCkZ7gOCYFE2IIIN3II"
ADMIN_CHAT_ID = -3548073076  

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)

# Хранилище статусов жалоб в памяти
complaints_db = {}

@app.route('/api/complaint', methods=['POST'])
def receive_complaint():
    data = request.json
    complaint_id = str(data.get('id', ''))
    sender = data.get('sender', '')
    target = data.get('target', '')
    reason = data.get('reason', '')
    proof_link = data.get('proofLink', '')
    file_data = data.get('fileData', '')

    # Записываем начальный статус
    complaints_db[complaint_id] = {
        "status": "На рассмотрении у админов",
        "statusClass": "status-pending"
    }

    text = (
        f"🚨 **Новая жалоба с сайта!**\n\n"
        f"👤 **От кого:** {sender}\n"
        f"🎯 **На кого:** {target}\n"
        f"📝 **Причина:** {reason}\n"
    )
    if proof_link:
        text += f"🔗 **Ссылка:** {proof_link}\n"

    # Кнопки для админов в чате
    markup = telebot.types.InlineKeyboardMarkup()
    btn_approve = telebot.types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{complaint_id}")
    btn_reject = telebot.types.InlineKeyboardButton("❌ Отказать", callback_data=f"reject_{complaint_id}")
    markup.add(btn_approve, btn_reject)

    try:
        if file_data and file_data.startswith('data:image'):
            header, encoded = file_data.split(",", 1)
            file_bytes = base64.b64decode(encoded)
            bot.send_photo(ADMIN_CHAT_ID, file_bytes, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(ADMIN_CHAT_ID, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

    return jsonify({"success": True})

# Эндпоинт для проверки статуса жалобы с сайта
@app.route('/api/status/<complaint_id>', methods=['GET'])
def get_status(complaint_id):
    if complaint_id in complaints_db:
        return jsonify(complaints_db[complaint_id])
    return jsonify({"status": "На рассмотрении у админов", "statusClass": "status-pending"})

# Обработка нажатий на кнопки в Telegram
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    parts = call.data.split('_')
    action = parts[0]
    c_id = parts[1]

    if c_id in complaints_db:
        if action == 'approve':
            complaints_db[c_id]["status"] = "Одобрено администрацией ✅"
            complaints_db[c_id]["statusClass"] = "status-approved"
            bot.answer_callback_query(call.id, "Жалоба успешно одобрена!")
            try:
                bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                                         caption=call.message.caption + "\n\n✅ **СТАТУС: ОДОБРЕНО**", 
                                         reply_markup=None, parse_mode="Markdown")
            except:
                bot.edit_message_text(call.message.chat.id, call.message.message_id, 
                                      text=call.message.text + "\n\n✅ **СТАТУС: ОДОБРЕНО**", 
                                      reply_markup=None, parse_mode="Markdown")

        elif action == 'reject':
            complaints_db[c_id]["status"] = "Отказано администрацией ❌"
            complaints_db[c_id]["statusClass"] = "status-rejected"
            bot.answer_callback_query(call.id, "Жалоба отклонена.")
            try:
                bot.edit_message_caption(call.message.chat.id, call.message.message_id, 
                                         caption=call.message.caption + "\n\n❌ **СТАТУС: ОТКАЗАНО**", 
                                         reply_markup=None, parse_mode="Markdown")
            except:
                bot.edit_message_text(call.message.chat.id, call.message.message_id, 
                                      text=call.message.text + "\n\n❌ **СТАТУС: ОТКАЗАНО**", 
                                      reply_markup=None, parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True)).start()
    app.run(host='0.0.0.0', port=5000)