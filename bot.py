import os, json, uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN: raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]
ADMIN_USERNAME = "MrKronick"
STAFF_GROUP_ID = -1003682731952
STAFF_INVITE_LINK = "https://t.me/+mgRGzcfEHfE4YWUy"

DATA_FILE = "ml_moderator_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PENDING_TAGS_FILE = "pending_tags.json"
REVIEWS_FILE = "reviews.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"

def load_json(filename, default=None):
    if default is None: default = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

app = Flask(__name__)
CORS(app)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route("/")
def home(): return "✅ Бот работает!"

@app.route("/ml-moderator-webhook", methods=["POST"])
def ml_moderator_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending = load_json(PENDING_CODES_FILE)
    if not code or code not in pending: return jsonify({"error": "Неверный код"}), 400
    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)
    apps = load_json(DATA_FILE, [])
    new_app = {
        "id": len(apps) + 1, "chat_id": chat_id, "real_name": data.get("real_name", "Игрок"),
        "minecraft_nick": data.get("minecraft_nick", ""), "telegram_user": data.get("telegram", ""),
        "age": data.get("age", ""), "experience": data.get("experience", ""),
        "motivation": data.get("motivation", ""),
        "rule_6_1": data.get("rule_6_1", ""), "rule_8_1": data.get("rule_8_1", ""),
        "rule_2_1": data.get("rule_2_1", ""), "rule_3_2": data.get("rule_3_2", ""),
        "rule_9_3": data.get("rule_9_3", ""), "rule_2_2_2_3": data.get("rule_2_2_2_3", ""),
        "rule_8_5": data.get("rule_8_5", ""), "agreement": data.get("agreement", "no"),
        "status": "pending", "submitted_at": datetime.now().isoformat(), "renamed_in_group": False
    }
    apps.append(new_app)
    save_json(DATA_FILE, apps)
    try: bot.send_message(chat_id, f"Привет {new_app['real_name']}! Твоя заявка на мл. модератора принята и будет рассмотрена в течение 3-5 дней. Ожидай.")
    except Exception as e: print(f"[ERROR] Отправка заявителю: {e}")
    for admin_id in ADMIN_IDS:
        try: bot.send_message(admin_id, f"🆕 Заявка на мл. модератора #{new_app['id']} от {new_app['real_name']}\nНик: {new_app['minecraft_nick']}\nTG: @{new_app.get('telegram_user','')}")
        except Exception as e: print(f"[ERROR] Отправка админу: {e}")
    return jsonify({"status": "ok", "app_id": new_app["id"]})

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK"
    return "Bad request", 400

@app.route("/api/reviews")
def api_reviews():
    reviews = load_json(REVIEWS_FILE, [])
    return jsonify(reviews)

def is_admin(user_id=None, username=None):
    if user_id and user_id in ADMIN_IDS: return True
    if username and username.lower() == ADMIN_USERNAME.lower(): return True
    return False

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("🔑 Получить код"), types.KeyboardButton("ℹ️ Помощь"))
    keyboard.add(types.KeyboardButton("💬 Оставить отзыв"))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    pending = load_json(PENDING_CODES_FILE)
    pending[code] = chat_id
    save_json(PENDING_CODES_FILE, pending)
    bot.send_message(chat_id, f"🌲 Добро пожаловать в FoggyLand!\n\nТвой код для заявки: `{code}`\nИспользуй кнопки ниже или введи /start для нового кода.", parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🔑 Получить код")
def button_get_code(message): start(message)

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Помощь")
def button_help(message):
    bot.send_message(message.chat.id, "🌲 **FoggyLand Bot**\n\n• 🔑 Получить код – для заявки на мл. модератора.\n• 💬 Оставить отзыв – поделиться мнением о сервере.\n• ℹ️ Помощь – эта подсказка.\n\nПравила: https://rules.foggyland.ru\nПо всем вопросам обращайтесь к администрации.", parse_mode="Markdown")

# ---------- ОТЗЫВЫ ----------
@bot.message_handler(commands=['отзыв'])
@bot.message_handler(func=lambda msg: msg.text == "💬 Оставить отзыв")
def ask_review(message):
    chat_id = message.chat.id
    sent = bot.send_message(chat_id, "Напиши свой отзыв о сервере, боте или команде. Он будет опубликован на сайте отзывов.")
    bot.register_next_step_handler(sent, process_review)

def process_review(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if len(text) < 3:
        bot.send_message(chat_id, "❌ Отзыв слишком короткий. Попробуй ещё раз: /отзыв")
        return
    if len(text) > 300:
        bot.send_message(chat_id, "❌ Отзыв слишком длинный (макс. 300 символов).")
        return

    reviews = load_json(REVIEWS_FILE, [])
    review = {
        "id": len(reviews) + 1,
        "chat_id": chat_id,
        "username": message.chat.username or "аноним",
        "text": text,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    reviews.append(review)
    save_json(REVIEWS_FILE, reviews)

    bot.send_message(chat_id, "✨ Спасибо за отзыв! Он появится в облаке отзывов на сайте.")
    for admin_id in ADMIN_IDS:
        try: bot.send_message(admin_id, f"💬 Новый отзыв от @{review['username']}:\n{text}")
        except: pass

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(user_id=message.from_user.id, username=message.from_user.username):
        bot.reply_to(message, "⛔ Нет доступа."); return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton("🛡️ Заявки на мл. модератора", callback_data="list_ml_moderator"))
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

@bot.message_handler(commands=['сменитьтег'])
def change_tag(message):
    if not is_admin(user_id=message.from_user.id, username=message.from_user.username):
        bot.reply_to(message, "⛔ Только владелец (@MrKronick) может менять теги."); return
    args = message.text.split()
    if len(args) < 3: bot.reply_to(message, "Использование: /сменитьтег @username НовыйТег"); return
    target_username, new_tag = args[1].lstrip('@'), " ".join(args[2:])
    try:
        admins = bot.get_chat_administrators(STAFF_GROUP_ID)
        target_user = next((a.user for a in admins if a.user.username and a.user.username.lower() == target_username.lower()), None)
        if not target_user: bot.reply_to(message, f"❌ Пользователь @{target_username} не найден."); return
        bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=target_user.id, custom_title=new_tag)
        bot.reply_to(message, f"✅ Тег для @{target_username} изменён на: **{new_tag}**", parse_mode="Markdown")
    except Exception as e: bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(content_types=['new_chat_members'])
def on_new_member(message):
    print(f"[LOG] Событие new_chat_members в чате {message.chat.id}. Участники: {[m.id for m in message.new_chat_members]}")
    if message.chat.id != STAFF_GROUP_ID:
        print(f"[LOG] Игнорируем — не наша группа (нужна {STAFF_GROUP_ID}, пришла {message.chat.id})")
        return

    pending_tags = load_json(PENDING_TAGS_FILE, [])
    apps = load_json(DATA_FILE, [])

    for new_member in message.new_chat_members:
        user_id = new_member.id
        print(f"[LOG] Обрабатываем пользователя {user_id}")

        tag_entry = next((t for t in pending_tags if t["chat_id"] == user_id), None)
        if tag_entry:
            nick = tag_entry["nick"]
            print(f"[LOG] Найден в очереди тегов: ник {nick}")
            try:
                bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                print(f"[OK] Тег '{nick}' установлен (из очереди).")
                pending_tags.remove(tag_entry)
                save_json(PENDING_TAGS_FILE, pending_tags)
                bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
            except Exception as e:
                print(f"[ERROR] Не удалось установить тег из очереди: {e}")
                try:
                    bot.promote_chat_member(chat_id=STAFF_GROUP_ID, user_id=user_id,
                        can_change_info=False, can_post_messages=False, can_edit_messages=False,
                        can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                        can_pin_messages=False, can_promote_members=False, can_manage_chat=False,
                        can_manage_video_chats=False)
                    bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                    pending_tags.remove(tag_entry)
                    save_json(PENDING_TAGS_FILE, pending_tags)
                    print(f"[OK] Тег '{nick}' установлен после промоушна.")
                    bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                except Exception as e2:
                    print(f"[ERROR] Не удалось даже после промоушна: {e2}")
        else:
            app = next((a for a in apps if a.get("chat_id") == user_id and a["status"] == "accepted" and not a.get("renamed_in_group")), None)
            if app:
                nick = app.get("minecraft_nick", "")
                print(f"[LOG] Найден в заявках #{app['id']}, ник: {nick}")
                try:
                    bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                    app["renamed_in_group"] = True
                    save_json(DATA_FILE, apps)
                    print(f"[OK] Тег '{nick}' установлен через заявку.")
                    bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                except Exception as e:
                    print(f"[ERROR] Установка тега через заявку: {e}")
                    try:
                        bot.promote_chat_member(chat_id=STAFF_GROUP_ID, user_id=user_id,
                            can_change_info=False, can_post_messages=False, can_edit_messages=False,
                            can_delete_messages=False, can_invite_users=False, can_restrict_members=False,
                            can_pin_messages=False, can_promote_members=False, can_manage_chat=False,
                            can_manage_video_chats=False)
                        bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                        app["renamed_in_group"] = True
                        save_json(DATA_FILE, apps)
                        print(f"[OK] Тег '{nick}' установлен после промоушна.")
                        bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                    except Exception as e2:
                        print(f"[ERROR] Не удалось даже после промоушна: {e2}")
            else:
                print(f"[LOG] Пользователь {user_id} не из нашей системы.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not is_admin(user_id=call.from_user.id, username=call.from_user.username):
        bot.answer_callback_query(call.id, "⛔ Нет доступа."); return
    data, apps = call.data, load_json(DATA_FILE, [])
    if data == "list_ml_moderator": show_ml_list(call, apps)
    elif data.startswith("ml_view_"):
        app = next((a for a in apps if a["id"] == int(data.split("_")[2])), None)
        if app: show_ml_detail(call, app)
    elif data.startswith("ml_accept_"): accept_ml_app(call, int(data.split("_")[2]), apps)
    elif data.startswith("ml_reject_"): reject_ml_app(call, int(data.split("_")[2]), apps)
    elif data == "back_to_admin": admin_panel(call.message)

def show_ml_list(call, apps):
    if not apps: bot.edit_message_text("📭 Заявок нет.", call.message.chat.id, call.message.message_id); return
    text, keyboard = "🛡️ Заявки на мл. модератора:\n\n", types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        emoji = "✅" if a["status"] == "accepted" else "❌" if a["status"] == "rejected" else "⏳"
        text += f"{emoji} #{a['id']} | {a['real_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(f"{emoji} #{a['id']} - {a['real_name']}", callback_data=f"ml_view_{a['id']}"))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_ml_detail(call, app):
    status = "✅ Принята" if app["status"] == "accepted" else "❌ Отклонена" if app["status"] == "rejected" else "⏳ Ожидает"
    text = (
        f"🛡️ Заявка на мл. модератора #{app['id']}\n\n"
        f"👤 Имя: {app['real_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: @{app.get('telegram_user','')}\n"
        f"🎂 Возраст: {app.get('age','')}\n"
        f"📊 Статус: {status}\n"
        f"🤝 Согласие с правилами: {'Да' if app.get('agreement') == 'yes' else 'Нет'}\n\n"
        f"🛠 Опыт: {app.get('experience','—')}\n"
        f"💬 Мотивация: {app.get('motivation','—')}\n\n"
        f"📜 Ответы на правила:\n"
        f"1. Читы (6.1): {app.get('rule_6_1','—')}\n"
        f"2. Гриферство (8.1): {app.get('rule_8_1','—')}\n"
        f"3. Оскорбления (2.1): {app.get('rule_2_1','—')}\n"
        f"4. Администраторам (3.2): {app.get('rule_3_2','—')}\n"
        f"5. Чужая территория (9.3): {app.get('rule_9_3','—')}\n"
        f"6. Спам/флуд (2.2-2.3): {app.get('rule_2_2_2_3','—')}\n"
        f"7. Обход бана (8.5): {app.get('rule_8_5','—')}"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if app["status"] == "pending":
        keyboard.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"ml_accept_{app['id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"ml_reject_{app['id']}")
        )
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_ml_moderator"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_ml_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id); return
    app["status"] = "accepted"
    chat_id, user_nick = app["chat_id"], app.get("minecraft_nick", "игрок")
    print(f"[LOG] Принимаем заявку #{app_id}, chat_id={chat_id}, ник={user_nick}")

    pending_tags = load_json(PENDING_TAGS_FILE, [])
    pending_tags.append({"chat_id": chat_id, "nick": user_nick})
    save_json(PENDING_TAGS_FILE, pending_tags)
    print(f"[LOG] Добавлен в очередь тегов: {chat_id} -> {user_nick}")

    try:
        bot.add_chat_member(chat_id=STAFF_GROUP_ID, user_id=chat_id)
        print(f"[OK] Пользователь {chat_id} добавлен напрямую!")
        bot.send_message(chat_id, "✅ Ты добавлен в группу модераторов FoggyLand! Тег будет выдан автоматически.")
        bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** присоединился!", parse_mode="Markdown")
    except Exception as e:
        print(f"[ERROR] add_chat_member: {e}")
        try:
            invite = bot.create_chat_invite_link(chat_id=STAFF_GROUP_ID, member_limit=1, name=f"Приглашение для {user_nick}")
            bot.send_message(chat_id, f"🎉 Поздравляю, {app['real_name']}!\n\nТвоя заявка одобрена!\nПерейди по ссылке для входа в группу:\n\n🔗 {invite.invite_link}\n\nПосле входа тебе автоматически выдадут тег.", disable_web_page_preview=True)
            bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** скоро присоединится по приглашению.", parse_mode="Markdown")
            print(f"[OK] Отправлена ссылка-приглашение для {chat_id}")
        except Exception as e2:
            print(f"[ERROR] create_chat_invite_link: {e2}")
            bot.send_message(chat_id, "⚠️ Не удалось добавить в группу. Администратор добавит вас вручную.")

    save_json(DATA_FILE, apps)
    bot.edit_message_text(f"✅ Заявка #{app_id} принята!", call.message.chat.id, call.message.message_id)

def reject_ml_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id); return
    app["status"] = "rejected"
    save_json(DATA_FILE, apps)
    try: bot.send_message(app["chat_id"], f"Привет {app['real_name']}. К сожалению, твоя заявка не прошла. Можешь подать повторно через 7 дней.")
    except Exception as e: print(f"[ERROR] reject notify: {e}")
    bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    bot.set_webhook(url=f"{RENDER_URL}/telegram")
    print(f"[START] Бот запущен. Группа: {STAFF_GROUP_ID}, Админы: {ADMIN_IDS}")
    app.run(host="0.0.0.0", port=PORT)
