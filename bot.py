import os, json, uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import telebot
from telebot import types

# ---------- КОНФИГУРАЦИЯ ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN: raise ValueError("TELEGRAM_TOKEN не установлен!")

ADMIN_IDS = [5145474067]
ADMIN_USERNAME = "MrKronick"
STAFF_GROUP_ID = -1003682731952
STAFF_INVITE_LINK = "https://t.me/+mgRGzcfEHfE4YWUy"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "foggy2026")

DATA_FILE = "ml_moderator_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PENDING_TAGS_FILE = "pending_tags.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"

# ---------- ХРАНИЛИЩЕ ----------
def load_json(filename, default=None):
    if default is None: default = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f: return json.load(f)
    return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- FLASK ----------
app = Flask(__name__)
CORS(app)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# ---------- МАРШРУТЫ ----------
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

# ---------- АДМИН-ПАНЕЛЬ ----------
@app.route("/admin-panel")
def admin_panel_page():
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "Доступ запрещён. Укажите правильный пароль: ?pwd=...", 403
    # Красивый HTML с встроенными стилями и скриптами
    return render_template_string('''
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FoggyLand · Админ-панель</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0a1f0e;
      --card: rgba(18, 30, 18, 0.8);
      --border: rgba(100, 170, 80, 0.3);
      --accent: #6fb85a;
      --text: #d0e6d5;
      --muted: #8aa87c;
      --radius: 1.5rem;
      --shadow: 0 20px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(90,150,80,0.2);
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', sans-serif;
      background: radial-gradient(circle at 20% 30%, #1a3b2e, #0b1f17);
      min-height: 100vh;
      padding: 2rem;
      color: var(--text);
      position: relative;
      overflow-x: hidden;
    }
    /* Анимированный фон */
    .bg-fog {
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="30" r="40" fill="rgba(100,180,100,0.05)"/><circle cx="80" cy="70" r="50" fill="rgba(60,120,60,0.04)"/></svg>');
      animation: fog 30s infinite alternate;
      z-index: 0;
    }
    @keyframes fog { 0% { opacity: 0.3; transform: scale(1); } 100% { opacity: 0.6; transform: scale(1.02); } }
    .container { position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; }
    h1 {
      font-size: 2.5rem; font-weight: 800;
      background: linear-gradient(180deg, #d4f0c0 0%, #7fa86b 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      text-align: center; margin-bottom: 0.5rem;
    }
    .subtitle { text-align: center; color: var(--muted); margin-bottom: 2rem; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1.5rem; }
    .app-card {
      background: var(--card); backdrop-filter: blur(15px);
      border: 1px solid var(--border); border-radius: var(--radius);
      padding: 1.5rem; box-shadow: var(--shadow);
      transition: all 0.3s ease;
      display: flex; flex-direction: column;
    }
    .app-card:hover { transform: translateY(-5px); border-color: var(--accent); box-shadow: 0 25px 45px rgba(0,0,0,0.5), 0 0 0 1px var(--accent); }
    .app-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .app-id { font-weight: 700; color: var(--accent); font-size: 1.1rem; }
    .app-status { font-size: 0.85rem; padding: 0.3rem 0.8rem; border-radius: 2rem; font-weight: 600; }
    .status-pending { background: rgba(255,200,50,0.15); color: #f0c060; }
    .status-accepted { background: rgba(100,200,80,0.15); color: #7cc96b; }
    .status-rejected { background: rgba(220,80,80,0.15); color: #e07070; }
    .app-name { font-size: 1.3rem; font-weight: 600; margin-bottom: 0.3rem; }
    .app-nick { color: var(--muted); margin-bottom: 0.8rem; }
    .app-tg { color: var(--accent); text-decoration: none; font-weight: 500; }
    .details-btn {
      background: rgba(100,160,80,0.2); border: 1px solid var(--border);
      color: var(--text); padding: 0.5rem 1rem; border-radius: 2rem;
      cursor: pointer; font-weight: 500; margin-top: 0.8rem;
      transition: 0.2s;
    }
    .details-btn:hover { background: rgba(100,160,80,0.4); }
    .app-actions { display: flex; gap: 0.5rem; margin-top: auto; padding-top: 1rem; }
    .btn {
      flex: 1; padding: 0.6rem; border-radius: 2rem; font-weight: 600;
      cursor: pointer; border: none; transition: 0.2s; font-size: 0.9rem;
    }
    .btn-accept { background: #2d8a3e; color: white; }
    .btn-accept:hover { background: #3ca64e; }
    .btn-reject { background: #8a3a3a; color: white; }
    .btn-reject:hover { background: #a64a4a; }
    .details-panel {
      display: none; margin-top: 1rem; padding: 1rem;
      background: rgba(0,0,0,0.2); border-radius: 1rem;
      border: 1px solid var(--border);
    }
    .details-panel.open { display: block; }
    .details-panel p { margin-bottom: 0.5rem; font-size: 0.9rem; }
    .details-panel strong { color: var(--accent); }
    .empty { text-align: center; color: var(--muted); font-size: 1.2rem; margin-top: 3rem; }
  </style>
</head>
<body>
<div class="bg-fog"></div>
<div class="container">
  <h1>🌲 FoggyLand</h1>
  <p class="subtitle">Административная панель заявок на мл. модератора</p>
  <div id="apps-container" class="card-grid"></div>
  <div id="empty-message" class="empty" style="display:none;">Заявок пока нет</div>
</div>
<script>
  const PASSWORD = '{{ password }}';
  const API_BASE = window.location.origin;

  async function loadApps() {
    try {
      const res = await fetch(`${API_BASE}/api/applications?password=${PASSWORD}`);
      if (!res.ok) throw new Error('Ошибка загрузки');
      const apps = await res.json();
      renderApps(apps);
    } catch (e) {
      document.getElementById('apps-container').innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
  }

  function renderApps(apps) {
    const container = document.getElementById('apps-container');
    const emptyMsg = document.getElementById('empty-message');
    if (!apps || apps.length === 0) {
      container.innerHTML = '';
      emptyMsg.style.display = 'block';
      return;
    }
    emptyMsg.style.display = 'none';
    let html = '';
    apps.forEach(app => {
      const statusClass = app.status === 'accepted' ? 'status-accepted' : (app.status === 'rejected' ? 'status-rejected' : 'status-pending');
      const statusText = app.status === 'accepted' ? 'Принята' : (app.status === 'rejected' ? 'Отклонена' : 'Ожидает');
      html += `
        <div class="app-card">
          <div class="app-header">
            <span class="app-id">#${app.id}</span>
            <span class="app-status ${statusClass}">${statusText}</span>
          </div>
          <div class="app-name">${app.real_name}</div>
          <div class="app-nick">⛏ ${app.minecraft_nick}</div>
          <div><a class="app-tg" href="https://t.me/${app.telegram_user}" target="_blank">@${app.telegram_user}</a></div>
          <button class="details-btn" onclick="toggleDetails(${app.id})">📋 Детали</button>
          <div class="details-panel" id="details-${app.id}">
            <p><strong>Возраст:</strong> ${app.age || '—'}</p>
            <p><strong>Опыт:</strong> ${app.experience || '—'}</p>
            <p><strong>Мотивация:</strong> ${app.motivation || '—'}</p>
            <p><strong>Согласие:</strong> ${app.agreement === 'yes' ? 'Да' : 'Нет'}</p>
            <p><strong>Ответы на правила:</strong></p>
            <ol style="margin-left:1.2rem;">
              <li><strong>Читы (6.1):</strong> ${app.rule_6_1 || '—'}</li>
              <li><strong>Гриферство (8.1):</strong> ${app.rule_8_1 || '—'}</li>
              <li><strong>Оскорбления (2.1):</strong> ${app.rule_2_1 || '—'}</li>
              <li><strong>Администраторам (3.2):</strong> ${app.rule_3_2 || '—'}</li>
              <li><strong>Чужая территория (9.3):</strong> ${app.rule_9_3 || '—'}</li>
              <li><strong>Спам/флуд (2.2-2.3):</strong> ${app.rule_2_2_2_3 || '—'}</li>
              <li><strong>Обход бана (8.5):</strong> ${app.rule_8_5 || '—'}</li>
            </ol>
          </div>
          ${app.status === 'pending' ? `
            <div class="app-actions">
              <button class="btn btn-accept" onclick="handleAction(${app.id}, 'accept')">✅ Принять</button>
              <button class="btn btn-reject" onclick="handleAction(${app.id}, 'reject')">❌ Отклонить</button>
            </div>
          ` : ''}
        </div>`;
    });
    container.innerHTML = html;
  }

  function toggleDetails(id) {
    const panel = document.getElementById(`details-${id}`);
    if (panel) panel.classList.toggle('open');
  }

  async function handleAction(id, action) {
    if (!confirm(`Вы уверены, что хотите ${action === 'accept' ? 'принять' : 'отклонить'} заявку #${id}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, password: PASSWORD })
      });
      if (res.ok) { loadApps(); }
      else alert('Ошибка обработки');
    } catch (e) { alert('Сетевая ошибка'); }
  }

  loadApps();
</script>
</body>
</html>
''', password=ADMIN_PASSWORD)

# ---------- API ДЛЯ АДМИНКИ ----------
@app.route("/api/applications")
def api_applications():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    return jsonify(load_json(DATA_FILE, []))

@app.route("/api/accept", methods=["POST"])
def api_accept():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found"}), 404
    accept_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

@app.route("/api/reject", methods=["POST"])
def api_reject():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found"}), 404
    reject_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ВЕБ-ПАНЕЛИ ----------
def accept_ml_app_web(app, apps):
    app["status"] = "accepted"
    chat_id, user_nick = app["chat_id"], app.get("minecraft_nick", "игрок")
    pending_tags = load_json(PENDING_TAGS_FILE, [])
    pending_tags.append({"chat_id": chat_id, "nick": user_nick})
    save_json(PENDING_TAGS_FILE, pending_tags)
    try:
        bot.add_chat_member(chat_id=STAFF_GROUP_ID, user_id=chat_id)
        bot.send_message(chat_id, "✅ Ты добавлен в группу модераторов FoggyLand! Тег будет выдан автоматически.")
        bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** присоединился!", parse_mode="Markdown")
    except:
        try:
            invite = bot.create_chat_invite_link(chat_id=STAFF_GROUP_ID, member_limit=1, name=f"Приглашение для {user_nick}")
            bot.send_message(chat_id, f"🎉 Поздравляю, {app['real_name']}!\n\nТвоя заявка одобрена!\nПерейди по ссылке для входа в группу:\n\n🔗 {invite.invite_link}\n\nПосле входа тебе автоматически выдадут тег.", disable_web_page_preview=True)
            bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** скоро присоединится по приглашению.", parse_mode="Markdown")
        except: bot.send_message(chat_id, "⚠️ Не удалось добавить в группу. Администратор добавит вас вручную.")
    save_json(DATA_FILE, apps)

def reject_ml_app_web(app, apps):
    app["status"] = "rejected"
    save_json(DATA_FILE, apps)
    try: bot.send_message(app["chat_id"], f"Привет {app['real_name']}. К сожалению, твоя заявка не прошла. Можешь подать повторно через 7 дней.")
    except: pass

# ========== TELEGRAM BOT ==========
def is_admin(user_id=None, username=None):
    if user_id and user_id in ADMIN_IDS: return True
    if username and username.lower() == ADMIN_USERNAME.lower(): return True
    return False

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(types.KeyboardButton("🔑 Получить код"), types.KeyboardButton("ℹ️ Помощь"))
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
    bot.send_message(message.chat.id, "🌲 **FoggyLand Bot**\n\n• 🔑 Получить код – для заявки на мл. модератора.\n• ℹ️ Помощь – эта подсказка.\n\nПравила: https://rules.foggyland.ru", parse_mode="Markdown")

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
    if message.chat.id != STAFF_GROUP_ID: return
    for new_member in message.new_chat_members:
        user_id = new_member.id
        pending_tags = load_json(PENDING_TAGS_FILE, [])
        tag_entry = next((t for t in pending_tags if t["chat_id"] == user_id), None)
        if tag_entry:
            nick = tag_entry["nick"]
            try:
                bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                pending_tags.remove(tag_entry)
                save_json(PENDING_TAGS_FILE, pending_tags)
                bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
            except:
                try:
                    bot.promote_chat_member(chat_id=STAFF_GROUP_ID, user_id=user_id, can_manage_chat=False)
                    bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                    pending_tags.remove(tag_entry)
                    save_json(PENDING_TAGS_FILE, pending_tags)
                    bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                except: pass
        else:
            apps = load_json(DATA_FILE, [])
            app = next((a for a in apps if a.get("chat_id") == user_id and a["status"] == "accepted" and not a.get("renamed_in_group")), None)
            if app:
                nick = app.get("minecraft_nick", "")
                try:
                    bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                    app["renamed_in_group"] = True
                    save_json(DATA_FILE, apps)
                    bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                except:
                    try:
                        bot.promote_chat_member(chat_id=STAFF_GROUP_ID, user_id=user_id, can_manage_chat=False)
                        bot.set_chat_administrator_custom_title(chat_id=STAFF_GROUP_ID, user_id=user_id, custom_title=nick)
                        app["renamed_in_group"] = True
                        save_json(DATA_FILE, apps)
                        bot.send_message(STAFF_GROUP_ID, f"👋 Добро пожаловать! Твой тег: **{nick}**", parse_mode="Markdown")
                    except: pass

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
    if not app or app["status"] != "pending": bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id); return
    accept_ml_app_web(app, apps)
    bot.edit_message_text(f"✅ Заявка #{app_id} принята!", call.message.chat.id, call.message.message_id)

def reject_ml_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": bot.edit_message_text("❌ Не найдена.", call.message.chat.id, call.message.message_id); return
    reject_ml_app_web(app, apps)
    bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    bot.set_webhook(url=f"{RENDER_URL}/telegram")
    app.run(host="0.0.0.0", port=PORT)
