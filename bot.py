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
DATA_FILE = "applications.json"
ADMIN_APPS_FILE = "admin_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
LINKED_FILE = "linked_accounts.json"
PROFILES_FILE = "profiles.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"   # ❗ замени на свой

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

# ----- Webhook для модераторской заявки -----
@app.route("/webhook", methods=["POST"])
def moderator_webhook():
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
    experience = data.get("experience", "")
    motivation = data.get("motivation", "")
    attitude = data.get("attitude_to_cheats", "")

    apps = load_json(DATA_FILE, [])
    new_app = {
        "id": len(apps) + 1,
        "chat_id": chat_id,
        "real_name": real_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "experience": experience,
        "motivation": motivation,
        "attitude_to_cheats": attitude,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    apps.append(new_app)
    save_json(DATA_FILE, apps)

    try:
        bot.send_message(chat_id, f"Привет {real_name}! Твоя заявка рассмотрится в течении недели. Ожидай.")
    except:
        pass
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🆕 Новая заявка #{new_app['id']} от {real_name}\nНик: {nick}\nTG: @{tg}")
        except:
            pass
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ----- Webhook для админской заявки -----
@app.route("/admin-webhook", methods=["POST"])
def admin_webhook():
    data = request.get_json(force=True) if request.is_json else request.form
    code = data.get("verification_code", "").strip().upper()
    pending = load_json(PENDING_CODES_FILE)
    if not code or code not in pending:
        return jsonify({"error": "Неверный код подтверждения"}), 400

    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)

    full_name = data.get("fullName", "Игрок")
    nick = data.get("minecraftNick", "")
    tg = data.get("telegram", "")
    # все остальные поля
    admin_apps = load_json(ADMIN_APPS_FILE, [])
    new_app = {
        "id": len(admin_apps) + 1,
        "chat_id": chat_id,
        "full_name": full_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
        # можно добавить все поля из формы
    }
    admin_apps.append(new_app)
    save_json(ADMIN_APPS_FILE, admin_apps)

    try:
        bot.send_message(chat_id, f"Привет {full_name}! Твоя заявка на администратора принята и будет рассмотрена в течение 5-7 дней. Ожидай.")
    except:
        pass
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"🆕 Заявка на администратора #{new_app['id']} от {full_name}\nНик: {nick}\nTG: @{tg}")
        except:
            pass
    return jsonify({"status": "ok", "app_id": new_app["id"]})

# ----- Webhook для привязки Minecraft -----
@app.route("/link-minecraft", methods=["POST"])
def link_minecraft():
    data = request.get_json(force=True)
    code = data.get("code", "").strip().upper()
    uuid = data.get("uuid")
    name = data.get("name")

    pending = load_json(PENDING_CODES_FILE)
    if code not in pending:
        return jsonify({"status": "error", "error": "Неверный код"}), 400

    chat_id = pending.pop(code)
    save_json(PENDING_CODES_FILE, pending)

    # сохраняем привязку
    links = load_json(LINKED_FILE, [])
    links = [l for l in links if l["chat_id"] != chat_id and l["uuid"] != uuid]
    links.append({"chat_id": chat_id, "uuid": uuid, "name": name, "linked_at": datetime.now().isoformat()})
    save_json(LINKED_FILE, links)

    # создаём/обновляем профиль
    profiles = load_json(PROFILES_FILE, [])
    exist = next((p for p in profiles if p["chat_id"] == chat_id), None)
    if not exist:
        profiles.append({
            "chat_id": chat_id,
            "minecraft_uuid": uuid,
            "minecraft_nick": name,
            "role": "none",
            "status": "active",
            "real_name": "",
            "age": "",
            "timezone": "",
            "experience": "",
            "skills": "",
            "contacts": "",
            "about": "",
            "last_updated": datetime.now().isoformat()
        })
        save_json(PROFILES_FILE, profiles)

    try:
        bot.send_message(chat_id, f"✅ Minecraft аккаунт **{name}** привязан! Теперь доступен профиль.")
        # обновим клавиатуру
        update_keyboard(chat_id)
    except:
        pass
    return jsonify({"status": "ok"})

# ========== TELEGRAM (вебхук) ==========
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    return "Bad request", 400

# ========== КЛАВИАТУРЫ ==========
def main_keyboard(chat_id):
    """Создаёт клавиатуру в зависимости от наличия профиля"""
    profiles = load_json(PROFILES_FILE, [])
    has_profile = any(p["chat_id"] == chat_id for p in profiles)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton("🔑 Получить код")]
    if has_profile:
        buttons.append(types.KeyboardButton("👤 Профиль"))
    buttons.append(types.KeyboardButton("🔗 Привязать Minecraft"))
    buttons.append(types.KeyboardButton("ℹ️ Помощь"))
    keyboard.add(*buttons)
    return keyboard

def update_keyboard(chat_id):
    """Отправляет обновлённую клавиатуру пользователю"""
    try:
        keyboard = main_keyboard(chat_id)
        bot.send_message(chat_id, "⌨️ Клавиатура обновлена.", reply_markup=keyboard)
    except:
        pass

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    code = f"FL-{uuid.uuid4().hex[:6].upper()}"
    pending = load_json(PENDING_CODES_FILE)
    pending[code] = chat_id
    save_json(PENDING_CODES_FILE, pending)

    text = (
        "🌲 Добро пожаловать в FoggyLand!\n\n"
        "Здесь вы можете:\n"
        "🔑 Получить код для заявки (модератор / админ)\n"
        "👤 Открыть профиль (после привязки Minecraft)\n"
        "🔗 Привязать свой Minecraft аккаунт\n\n"
        f"Текущий код: `{code}`\n(годен, пока не использован)"
    )
    keyboard = main_keyboard(chat_id)
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

# Кнопка "🔑 Получить код"
@bot.message_handler(func=lambda msg: msg.text == "🔑 Получить код")
def button_get_code(message):
    start(message)  # просто вызываем start

# Кнопка "👤 Профиль"
@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль")
def button_profile(message):
    chat_id = message.chat.id
    profiles = load_json(PROFILES_FILE, [])
    user = next((p for p in profiles if p["chat_id"] == chat_id), None)
    if not user:
        bot.send_message(chat_id, "❌ Профиль не найден. Сначала привяжите Minecraft (/link или кнопка «Привязать Minecraft»).")
        return
    show_profile(chat_id, user, editable=True)

# Кнопка "🔗 Привязать Minecraft"
@bot.message_handler(func=lambda msg: msg.text == "🔗 Привязать Minecraft")
def button_link(message):
    link_command(message)

# Кнопка "ℹ️ Помощь"
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Помощь")
def button_help(message):
    text = (
        "🌲 **FoggyLand Bot**\n\n"
        "• **🔑 Получить код** – выдаёт код для подачи заявки на модератора или администратора.\n"
        "• **👤 Профиль** – ваш профиль модератора/админа (доступен после привязки).\n"
        "• **🔗 Привязать Minecraft** – связывает ваш Telegram с игровым аккаунтом.\n"
        "• **ℹ️ Помощь** – это сообщение.\n\n"
        "По всем вопросам обращайтесь к администрации."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Команда /link (дублируем для текстовой кнопки)
@bot.message_handler(commands=['link'])
def link_command(message):
    chat_id = message.chat.id
    code = f"MC-{uuid.uuid4().hex[:6].upper()}"
    pending = load_json(PENDING_CODES_FILE)
    pending[code] = chat_id
    save_json(PENDING_CODES_FILE, pending)

    bot.send_message(chat_id,
        f"🎮 **Привязка Minecraft**\n\n"
        f"1. Зайди на сервер FoggyLand\n"
        f"2. Введи в чате: `/link {code}`\n"
        f"3. Готово!",
        parse_mode="Markdown")

# Команды /profile и /editprofile оставляем для совместимости (но можно скрыть)
@bot.message_handler(commands=['profile', 'p'])
def profile_cmd(message):
    button_profile(message)   # перенаправляем на кнопку

@bot.message_handler(commands=['editprofile'])
def editprofile_cmd(message):
    chat_id = message.chat.id
    profiles = load_json(PROFILES_FILE, [])
    user = next((p for p in profiles if p["chat_id"] == chat_id), None)
    if not user:
        bot.send_message(chat_id, "❌ Профиль не найден.")
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📛 Имя", callback_data="edit_realname"),
        types.InlineKeyboardButton("🎂 Возраст", callback_data="edit_age"),
        types.InlineKeyboardButton("🌍 Часовой пояс", callback_data="edit_timezone"),
        types.InlineKeyboardButton("🛠 Опыт", callback_data="edit_experience"),
        types.InlineKeyboardButton("⚙️ Навыки", callback_data="edit_skills"),
        types.InlineKeyboardButton("📞 Контакты", callback_data="edit_contacts"),
        types.InlineKeyboardButton("💬 О себе", callback_data="edit_about")
    )
    bot.send_message(chat_id, "✏️ Что хотите изменить?", reply_markup=keyboard)

# ========== АДМИНСКАЯ КОМАНДА (скрытая) ==========
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа.")
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📋 Заявки (модер)", callback_data="list_all"),
        types.InlineKeyboardButton("⏳ Ожидающие (модер)", callback_data="list_pending"),
        types.InlineKeyboardButton("✅ Принятые (модер)", callback_data="list_accepted"),
        types.InlineKeyboardButton("❌ Отклонённые (модер)", callback_data="list_rejected"),
        types.InlineKeyboardButton("👑 Админ-заявки", callback_data="list_admin_apps"),
        types.InlineKeyboardButton("🔍 Поиск профиля", callback_data="admin_search_profile")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

# ========== ОБРАБОТКА ИНЛАЙН‑КОЛЛБЭКОВ (заявки, профили, админка) ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    # ----- Заявки модератора -----
    if data in ("list_all", "list_pending", "list_accepted", "list_rejected"):
        apps = load_json(DATA_FILE, [])
        if data == "list_pending":
            apps = [a for a in apps if a["status"] == "pending"]
        elif data == "list_accepted":
            apps = [a for a in apps if a["status"] == "accepted"]
        elif data == "list_rejected":
            apps = [a for a in apps if a["status"] == "rejected"]
        show_list(call, apps, "mod")
        return

    if data.startswith("view_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        app = next((a for a in apps if a["id"] == app_id), None)
        if app:
            show_detail(call, app)
        return

    if data.startswith("accept_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        accept_app(call, app_id, apps)
        return

    if data.startswith("reject_"):
        app_id = int(data.split("_")[1])
        apps = load_json(DATA_FILE, [])
        reject_app(call, app_id, apps)
        return

    # ----- Админские заявки -----
    if data == "list_admin_apps":
        apps = load_json(ADMIN_APPS_FILE, [])
        show_admin_list(call, apps)
        return

    if data.startswith("admin_view_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        app = next((a for a in apps if a["id"] == app_id), None)
        if app:
            show_admin_detail(call, app)
        return

    if data.startswith("admin_accept_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        accept_admin_app(call, app_id, apps)
        return

    if data.startswith("admin_reject_"):
        app_id = int(data.split("_")[2])
        apps = load_json(ADMIN_APPS_FILE, [])
        reject_admin_app(call, app_id, apps)
        return

    # ----- Профили и админские действия с профилями -----
    if data.startswith("edit_") and not data.startswith("edit_profile_"):
        # редактирование поля профиля (для обычного пользователя)
        if call.from_user.id not in ADMIN_IDS:
            handle_profile_field_edit(call)
        else:
            # админ тоже может редактировать свои поля
            handle_profile_field_edit(call)
        return

    if data.startswith("edit_profile_"):
        target_id = int(data.split("_")[2])
        # открываем меню редактирования (только для владельца или админа)
        if call.from_user.id == target_id or call.from_user.id in ADMIN_IDS:
            profiles = load_json(PROFILES_FILE, [])
            user = next((p for p in profiles if p["chat_id"] == target_id), None)
            if user:
                editprofile_cmd(call.message)
        return

    if data == "back_to_admin":
        admin_panel(call.message)
        return

    # Админские коллбэки по профилям
    if data.startswith("admin_showprofile_"):
        target_id = int(data.split("_")[2])
        profiles = load_json(PROFILES_FILE, [])
        user = next((p for p in profiles if p["chat_id"] == target_id), None)
        if user:
            show_profile(chat_id, user, editable=True, is_admin=True)
        return

    if data.startswith("admin_changerole_"):
        target_id = int(data.split("_")[2])
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("Модератор", callback_data=f"setrole_{target_id}_moderator"),
            types.InlineKeyboardButton("Админ", callback_data=f"setrole_{target_id}_admin"),
            types.InlineKeyboardButton("Снять роль", callback_data=f"setrole_{target_id}_none")
        )
        bot.edit_message_text("Выберите новую роль:", chat_id, call.message.message_id, reply_markup=keyboard)
        return

    if data.startswith("setrole_"):
        parts = data.split("_")
        target_id = int(parts[1])
        role = parts[2]
        profiles = load_json(PROFILES_FILE, [])
        for p in profiles:
            if p["chat_id"] == target_id:
                p["role"] = role
                break
        save_json(PROFILES_FILE, profiles)
        bot.edit_message_text(f"✅ Роль изменена на {role}", chat_id, call.message.message_id)
        return

    if data.startswith("admin_changestatus_"):
        target_id = int(data.split("_")[2])
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            types.InlineKeyboardButton("Активен", callback_data=f"setstatus_{target_id}_active"),
            types.InlineKeyboardButton("Неактивен", callback_data=f"setstatus_{target_id}_inactive"),
            types.InlineKeyboardButton("Забанен", callback_data=f"setstatus_{target_id}_banned")
        )
        bot.edit_message_text("Выберите статус:", chat_id, call.message.message_id, reply_markup=keyboard)
        return

    if data.startswith("setstatus_"):
        parts = data.split("_")
        target_id = int(parts[1])
        status = parts[2]
        profiles = load_json(PROFILES_FILE, [])
        for p in profiles:
            if p["chat_id"] == target_id:
                p["status"] = status
                break
        save_json(PROFILES_FILE, profiles)
        bot.edit_message_text(f"✅ Статус изменён на {status}", chat_id, call.message.message_id)
        return

    if data == "admin_search_profile":
        msg = bot.send_message(chat_id, "Введите ник или UUID модератора:")
        bot.register_next_step_handler(msg, admin_search_profile_step)
        return

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def show_profile(chat_id, profile, editable=False, is_admin=False):
    role = profile.get("role", "нет")
    status = profile.get("status", "active")
    text = (
        f"👤 **Профиль**\n"
        f"⛏ Ник: {profile.get('minecraft_nick', '—')}\n"
        f"🎭 Роль: {role}\n"
        f"📌 Статус: {status}\n"
        f"📛 Настоящее имя: {profile.get('real_name', '—')}\n"
        f"🎂 Возраст: {profile.get('age', '—')}\n"
        f"🌍 Часовой пояс: {profile.get('timezone', '—')}\n"
        f"🛠 Опыт: {profile.get('experience', '—')}\n"
        f"⚙️ Навыки: {profile.get('skills', '—')}\n"
        f"📞 Контакты: {profile.get('contacts', '—')}\n"
        f"💬 О себе: {profile.get('about', '—')}\n"
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if editable and (chat_id == profile["chat_id"] or is_admin):
        keyboard.add(types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_profile_{profile['chat_id']}"))
    if is_admin:
        keyboard.add(
            types.InlineKeyboardButton("👑 Роль", callback_data=f"admin_changerole_{profile['chat_id']}"),
            types.InlineKeyboardButton("📌 Статус", callback_data=f"admin_changestatus_{profile['chat_id']}")
        )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)

def admin_search_profile_step(message):
    query = message.text.strip().lower()
    profiles = load_json(PROFILES_FILE, [])
    found = [p for p in profiles if p.get("minecraft_nick","").lower() == query or p.get("minecraft_uuid") == query]
    if not found:
        bot.send_message(message.chat.id, "❌ Профиль не найден.")
        return
    if len(found) == 1:
        show_profile(message.chat.id, found[0], editable=True, is_admin=True)
    else:
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for p in found:
            keyboard.add(types.InlineKeyboardButton(p["minecraft_nick"], callback_data=f"admin_showprofile_{p['chat_id']}"))
        bot.send_message(message.chat.id, "Найдено несколько профилей:", reply_markup=keyboard)

def handle_profile_field_edit(call):
    chat_id = call.from_user.id
    profiles = load_json(PROFILES_FILE, [])
    user = next((p for p in profiles if p["chat_id"] == chat_id), None)
    if not user:
        bot.answer_callback_query(call.id, "Профиль не найден")
        return
    field_map = {
        "edit_realname": "real_name",
        "edit_age": "age",
        "edit_timezone": "timezone",
        "edit_experience": "experience",
        "edit_skills": "skills",
        "edit_contacts": "contacts",
        "edit_about": "about"
    }
    if call.data not in field_map:
        bot.answer_callback_query(call.id, "Неизвестная команда")
        return
    field = field_map[call.data]
    msg = bot.send_message(chat_id, f"Введите новое значение для **{field.replace('_',' ')}** (или /cancel):")
    bot.register_next_step_handler(msg, process_field_input, user, field)
    bot.answer_callback_query(call.id)

def process_field_input(message, user, field):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "Изменение отменено.")
        return
    user[field] = message.text.strip()
    user["last_updated"] = datetime.now().isoformat()
    profiles = load_json(PROFILES_FILE, [])
    for i, p in enumerate(profiles):
        if p["chat_id"] == user["chat_id"]:
            profiles[i] = user
            break
    save_json(PROFILES_FILE, profiles)
    bot.send_message(message.chat.id, f"✅ Поле **{field.replace('_',' ')}** обновлено!")

# Функции показа заявок (оставлены в сокращённом виде, в реальном коде полностью из предыдущей версии)
def show_list(call, apps, app_type):
    # реализация аналогична предыдущей
    pass

def show_detail(call, app):
    pass

def accept_app(call, app_id, apps):
    pass

def reject_app(call, app_id, apps):
    pass

def show_admin_list(call, apps):
    pass

def show_admin_detail(call, app):
    pass

def accept_admin_app(call, app_id, apps):
    pass

def reject_admin_app(call, app_id, apps):
    pass

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
