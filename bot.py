import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

# ========== КОНФИГУРАЦИЯ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]   # ❗ Свой Telegram ID
DATA_FILE = "ml_moderator_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"   # ❗ свой Render URL

# Переменные для группы (установи их в Render)
STAFF_GROUP_ID = os.environ.get("STAFF_GROUP_ID", "-1003682731952")
STAFF_INVITE_LINK = os.environ.get("STAFF_INVITE_LINK", "https://t.me/+mgRGzcfEHfE4YWUy")

# ========== ХРАНИЛИЩЕ ==========
def load_json(filename, default=None):
    if default is None:
        default = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ========== FLASK ==========
app = Flask(__name__)
CORS(app)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@app.route("/")
def home():
    return "✅ Бот работает!"

# ----- Приём заявки на мл. модератора -----
@app.route("/ml-moderator-webhook", methods=["POST"])
def ml_moderator_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending = load_json(PENDING_CODES_FILE)
    if not code or code not in pending:
        return jsonify({"error": "Неверный код подтверждения"}), 400

    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)

    real_name = data.get("real_name", "Игрок")
    nick = data.get("minecraft_nick", "")
    tg = data.get("telegram", "")
    age = data.get("age", "")
    experience = data.get("experience", "")
    motivation = data.get("motivation", "")
    agreement = data.get("agreement", "no")

    apps = load_json(DATA_FILE, [])
    new_app = {
        "id": len(apps) + 1,
        "chat_id": chat_id,
        "real_name": real_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "age": age,
        "experience": experience,
        "motivation": motivation,
        "rule_6_1": data.get("rule_6_1", ""),
        "rule_8_1": data.get("rule_8_1", ""),
        "rule_2_1": data.get("rule_2_1", ""),
        "rule_3_2": data.get("rule_3_2", ""),
        "rule_9_3": data.get("rule_9_3", ""),
        "rule_2_2_2_3": data.get("rule_2_2_2_3", ""),
        "rule_8_5": data.get("rule_8_5", ""),
        "agreement": agreement,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    apps.append(new_app)
    save_json(DATA_FILE, apps)

    try:
        bot.send_message(chat_id,
                         f"Привет {real_name}! Твоя заявка на мл. модератора принята и будет рассмотрена в течение 3-5 дней. Ожидай.")
    except Exception as e:
        print(f"Ошибка отправки заявителю: {e}")

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                             f"🆕 Заявка на мл. модератора #{new_app['id']} от {real_name}\n"
                             f"Ник: {nick}\nTG: @{tg}")
        except:
            pass

    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ========== Telegram вебхук ==========
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    return "Bad request", 400

# ========== КЛАВИАТУРА ==========
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("🔑 Получить код"), types.KeyboardButton("ℹ️ Помощь"))
    return keyboard

# ========== ОБРАБОТЧИКИ КОМАНД ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    pending = load_json(PENDING_CODES_FILE)
    pending[code] = chat_id
    save_json(PENDING_CODES_FILE, pending)

    text = (
        "🌲 Добро пожаловать в FoggyLand!\n\n"
        f"Твой код для заявки: `{code}`\n"
        "Используй кнопки ниже или введи /start для нового кода."
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🔑 Получить код")
def button_get_code(message):
    start(message)

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Помощь")
def button_help(message):
    text = (
        "🌲 **FoggyLand Bot**\n\n"
        "• **🔑 Получить код** – выдаёт код для подачи заявки на мл. модератора.\n"
        "• **ℹ️ Помощь** – эта подсказка.\n\n"
        "Правила сервера: https://rules.foggyland.ru\n"
        "По всем вопросам обращайтесь к администрации."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Админ-панель (скрытая команда)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа.")
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🛡️ Заявки на мл. модератора", callback_data="list_ml_moderator")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

# ========== ОБРАБОТКА ЗАЯВОК (мл. модератор) ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    data = call.data

    if data == "list_ml_moderator":
        apps = load_json(DATA_FILE, [])
        show_ml_list(call, apps)
        return

    if data.startswith("ml_view_"):
        app_id = int(data.split("_")[2])
        apps = load_json(DATA_FILE, [])
        app = next((a for a in apps if a["id"] == app_id), None)
        if app:
            show_ml_detail(call, app)
        return

    if data.startswith("ml_accept_"):
        app_id = int(data.split("_")[2])
        apps = load_json(DATA_FILE, [])
        accept_ml_app(call, app_id, apps)
        return

    if data.startswith("ml_reject_"):
        app_id = int(data.split("_")[2])
        apps = load_json(DATA_FILE, [])
        reject_ml_app(call, app_id, apps)
        return

    if data == "back_to_admin":
        admin_panel(call.message)
        return

# ========== ФУНКЦИИ ДЛЯ ЗАЯВОК МЛ. МОДЕРАТОРА ==========
def show_ml_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Заявок на мл. модератора нет.", call.message.chat.id, call.message.message_id)
        return
    text = "🛡️ Заявки на мл. модератора:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        emoji = "✅" if a["status"] == "accepted" else "❌" if a["status"] == "rejected" else "⏳"
        text += f"{emoji} #{a['id']} | {a['real_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {a['real_name']}",
            callback_data=f"ml_view_{a['id']}"
        ))
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
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return

    app["status"] = "accepted"

    # ---------- АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ В ГРУППУ ----------
    group_id = int(STAFF_GROUP_ID) if STAFF_GROUP_ID.lstrip('-').isdigit() else None
    chat_id = app["chat_id"]
    user_nick = app.get("minecraft_nick", "игрок")

    added_to_group = False
    if group_id:
        try:
            # Пробуем добавить напрямую (если бот может приглашать)
            bot.add_chat_member(chat_id=group_id, user_id=chat_id)
            added_to_group = True
            bot.send_message(chat_id, "✅ Ты был автоматически добавлен в группу модераторов FoggyLand!")
        except Exception as e:
            print(f"Не удалось добавить напрямую: {e}")
            # fallback — создаём ссылку-приглашение
            try:
                invite = bot.create_chat_invite_link(
                    chat_id=group_id,
                    member_limit=1,
                    name=f"Приглашение для {user_nick}"
                )
                personal_link = invite.invite_link
                bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🎉 Поздравляю, {app['real_name']}!\n\n"
                        f"Твоя заявка на мл. модератора одобрена!\n"
                        f"Чтобы присоединиться к команде, перейди по ссылке:\n\n"
                        f"🔗 {personal_link}\n\n"
                        f"После входа представься: ник {user_nick}, роль — мл. модератор."
                    ),
                    disable_web_page_preview=True
                )
            except Exception as e2:
                print(f"Не удалось создать ссылку: {e2}")
                bot.send_message(chat_id, "⚠️ Не удалось добавить в группу. Администратор сделает это вручную.")
    else:
        bot.send_message(chat_id, "⚠️ ID группы не настроен. Администратор добавит вас вручную.")

    # Уведомление в группу
    if group_id:
        try:
            bot.send_message(
                chat_id=group_id,
                text=f"👋 Новый мл. модератор **{user_nick}** {'присоединился' if added_to_group else 'скоро присоединится'}!",
                parse_mode="Markdown"
            )
        except:
            pass

    save_json(DATA_FILE, apps)
    # ---------- КОНЕЦ ДОБАВЛЕНИЯ ----------

    bot.edit_message_text(f"✅ Заявка #{app_id} принята!", call.message.chat.id, call.message.message_id)

def reject_ml_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(DATA_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['real_name']}. К сожалению, твоя заявка на мл. модератора не прошла. Можешь подать повторно через 7 дней.")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена! Уведомление отправлено.", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("🧹 Старый webhook удалён")
    except:
        pass
    webhook_url = f"{RENDER_URL}/telegram"
    try:
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен на {webhook_url}")
    except Exception as e:
        print(f"❌ Ошибка webhook: {e}")
    app.run(host="0.0.0.0", port=PORT)
