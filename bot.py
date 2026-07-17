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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "foggy2026")

DATA_FILE = "ml_moderator_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PENDING_TAGS_FILE = "pending_tags.json"
MESSAGES_FILE = "user_messages.json"
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

# ---------- ВСТРОЕННАЯ АДМИН-ПАНЕЛЬ ----------
ADMIN_PANEL_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>FoggyLand Admin</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: radial-gradient(circle at 20% 30%, #1f3b1f, #0a1a0a);
      min-height: 100vh;
      padding: 2rem 1.5rem;
      color: #d0e6d5;
      position: relative;
      overflow-x: hidden;
    }
    body::before {
      content: "";
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400"><filter id="fog"><feTurbulence baseFrequency="0.02" numOctaves="4" result="turbulence"/><feDisplacementMap in="SourceGraphic" in2="turbulence" scale="30" xChannelSelector="R" yChannelSelector="G"/></filter><circle cx="200" cy="200" r="150" fill="rgba(180,220,160,0.15)" filter="url(#fog)"/></svg>');
      background-size: cover;
      z-index: 0;
    }
    .container {
      max-width: 1100px;
      margin: 0 auto;
      position: relative;
      z-index: 2;
    }
    h1 {
      font-size: 2.8rem;
      font-weight: 800;
      background: linear-gradient(180deg, #d4f0c0, #7fa86b);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      text-align: center;
      margin-bottom: 0.5rem;
      text-shadow: 0 0 20px rgba(80,150,60,0.5);
    }
    .subtitle {
      text-align: center;
      color: #a0c090;
      margin-bottom: 2rem;
      font-weight: 500;
      backdrop-filter: blur(10px);
      background: rgba(20,30,18,0.5);
      display: inline-block;
      padding: 0.4rem 2rem;
      border-radius: 3rem;
      margin-left: auto; margin-right: auto; width: fit-content;
      border: 1px solid #5e874b;
    }
    .table-wrapper {
      background: rgba(10,20,12,0.7);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-radius: 2rem;
      padding: 1.5rem;
      box-shadow: 0 30px 50px -20px rgba(0,0,0,0.7), 0 0 0 1px rgba(100,150,90,0.4);
      border: 1px solid rgba(120,170,80,0.3);
      overflow-x: auto;
      margin-bottom: 2rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.95rem;
    }
    th, td {
      padding: 0.9rem 1rem;
      text-align: left;
      border-bottom: 1px solid rgba(90,150,100,0.25);
    }
    th {
      background: rgba(30,50,30,0.6);
      color: #c0e0b0;
      font-weight: 600;
      position: sticky;
      top: 0;
    }
    tr:hover td { background: rgba(60,90,40,0.3); transition: 0.2s; }
    .badge {
      padding: 0.3rem 0.8rem;
      border-radius: 2rem;
      font-weight: 600;
      font-size: 0.85rem;
    }
    .badge-pending { background: #5a5a30; color: #ffffb0; }
    .badge-accepted { background: #2d6a2d; color: #c0ffc0; }
    .badge-rejected { background: #6a2d2d; color: #ffc0c0; }
    .btn {
      padding: 0.5rem 1.2rem;
      border: none;
      border-radius: 1.2rem;
      font-weight: 600;
      cursor: pointer;
      transition: 0.2s;
      font-size: 0.85rem;
      margin: 0.2rem;
    }
    .btn-accept { background: #2d6a2d; color: white; }
    .btn-accept:hover { background: #3e8e3e; transform: scale(0.97); }
    .btn-reject { background: #6a2d2d; color: white; }
    .btn-reject:hover { background: #8e3e3e; transform: scale(0.97); }
    .btn-details { background: rgba(80,130,60,0.3); color: #c0e0b0; backdrop-filter: blur(5px); }
    .btn-details:hover { background: rgba(80,130,60,0.5); }
    .btn-messages { background: rgba(80,130,160,0.3); color: #c0d0e0; backdrop-filter: blur(5px); }
    .btn-messages:hover { background: rgba(80,130,160,0.5); }
    .modal {
      display: none;
      position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.7); backdrop-filter: blur(10px);
      z-index: 1000; justify-content: center; align-items: center;
    }
    .modal.active { display: flex; }
    .modal-content {
      background: rgba(20,30,18,0.95); backdrop-filter: blur(25px);
      border: 1px solid #5e874b; border-radius: 2rem;
      padding: 2rem; max-width: 600px; width: 90%;
      max-height: 80vh; overflow-y: auto;
      box-shadow: 0 40px 60px -15px rgba(0,0,0,0.8);
    }
    .modal-content h3 { color: #9bc17a; margin-bottom: 1rem; }
    .modal-content p { margin-bottom: 0.5rem; }
    .close-btn {
      float: right; background: none; border: none; color: #a0c090;
      font-size: 1.5rem; cursor: pointer;
    }
    .loading, .empty { text-align: center; padding: 2rem; color: #80a070; }
    @media (max-width: 700px) {
      th, td { padding: 0.6rem; font-size: 0.8rem; }
      .btn { padding: 0.4rem 0.8rem; font-size: 0.75rem; }
    }
  </style>
</head>
<body>
<div class="container">
  <h1>👑 FoggyLand</h1>
  <div class="subtitle">Админ-панель</div>

  <div class="table-wrapper" id="apps-container">
    <div class="loading">Загрузка заявок...</div>
  </div>

  <div style="text-align:center; margin-bottom:2rem;">
    <button class="btn btn-messages" onclick="loadMessages()">💬 Сообщения от пользователей</button>
  </div>
  <div class="table-wrapper" id="messages-container" style="display:none;"></div>
</div>

<div class="modal" id="detailsModal">
  <div class="modal-content" id="modalContent"></div>
</div>

<script>
  const PASSWORD = 'foggy2026';
  const API_BASE = window.location.origin;

  async function fetchApps() {
    try {
      const res = await fetch(`${API_BASE}/api/applications?password=${PASSWORD}`);
      if (!res.ok) throw new Error('Ошибка');
      return await res.json();
    } catch(e) {
      document.getElementById('apps-container').innerHTML = '<div class="empty">❌ Ошибка загрузки</div>';
      return [];
    }
  }

  async function renderApps() {
    const apps = await fetchApps();
    const container = document.getElementById('apps-container');
    if (!apps.length) {
      container.innerHTML = '<div class="empty">📭 Заявок пока нет</div>';
      return;
    }
    let html = `<table><thead><tr>
      <th>ID</th><th>Имя</th><th>Ник Minecraft</th><th>Telegram</th><th>Статус</th><th>Действия</th>
    </tr></thead><tbody>`;
    apps.forEach(app => {
      const s = app.status;
      const badge = s === 'accepted' ? 'badge-accepted' : (s === 'rejected' ? 'badge-rejected' : 'badge-pending');
      const txt = s === 'accepted' ? '✅ Принята' : (s === 'rejected' ? '❌ Отклонена' : '⏳ Ожидает');
      html += `<tr>
        <td>#${app.id}</td>
        <td>${esc(app.real_name)}</td>
        <td>${esc(app.minecraft_nick)}</td>
        <td>@${esc(app.telegram_user || '')}</td>
        <td><span class="badge ${badge}">${txt}</span></td>
        <td>
          <button class="btn btn-details" onclick="showDetails(${app.id})">📋</button>
          ${s === 'pending' ? `<button class="btn btn-accept" onclick="act(${app.id},'accept')">✅</button>
           <button class="btn btn-reject" onclick="act(${app.id},'reject')">❌</button>` : ''}
        </td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  function esc(t) { return (t||'').replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[m]); }

  async function act(id, action) {
    if (!confirm(`Точно ${action==='accept'?'принять':'отклонить'} заявку #${id}?`)) return;
    try {
      const r = await fetch(`${API_BASE}/api/${action}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id, password: PASSWORD})
      });
      const d = await r.json();
      if (r.ok) { alert('Готово!'); renderApps(); }
      else alert('Ошибка: ' + (d.error || ''));
    } catch(e) { alert('Сетевая ошибка'); }
  }

  async function showDetails(id) {
    const apps = await fetchApps();
    const app = apps.find(a => a.id === id);
    if (!app) return;
    const mc = document.getElementById('modalContent');
    mc.innerHTML = `<button class="close-btn" onclick="document.getElementById('detailsModal').classList.remove('active')">✖</button>
      <h3>Заявка #${app.id}</h3>
      <p><b>Имя:</b> ${esc(app.real_name)}</p>
      <p><b>Ник:</b> ${esc(app.minecraft_nick)}</p>
      <p><b>Telegram:</b> @${esc(app.telegram_user || '')}</p>
      <p><b>Возраст:</b> ${esc(app.age || '')}</p>
      <p><b>Опыт:</b> ${esc(app.experience || '—')}</p>
      <p><b>Мотивация:</b> ${esc(app.motivation || '—')}</p>
      <p><b>Согласие:</b> ${app.agreement === 'yes' ? 'Да' : 'Нет'}</p>
      <h4 style="margin-top:1rem;">📜 Ответы на правила</h4>
      <ol>
        <li>Читы (6.1): ${esc(app.rule_6_1 || '—')}</li>
        <li>Гриферство (8.1): ${esc(app.rule_8_1 || '—')}</li>
        <li>Оскорбления (2.1): ${esc(app.rule_2_1 || '—')}</li>
        <li>Администраторам (3.2): ${esc(app.rule_3_2 || '—')}</li>
        <li>Территория (9.3): ${esc(app.rule_9_3 || '—')}</li>
        <li>Спам/флуд (2.2-2.3): ${esc(app.rule_2_2_2_3 || '—')}</li>
        <li>Обход бана (8.5): ${esc(app.rule_8_5 || '—')}</li>
      </ol>`;
    document.getElementById('detailsModal').classList.add('active');
  }

  // --- Сообщения ---
  async function loadMessages() {
    const container = document.getElementById('messages-container');
    container.style.display = 'block';
    container.innerHTML = '<div class="loading">Загрузка сообщений...</div>';
    try {
      const res = await fetch(`${API_BASE}/api/messages?password=${PASSWORD}`);
      const msgs = await res.json();
      if (!msgs.length) {
        container.innerHTML = '<div class="empty">💬 Нет сообщений.</div>';
        return;
      }
      let html = `<table><tr><th>От кого</th><th>Сообщение</th><th>Дата</th><th>Ответить</th></tr>`;
      msgs.reverse().forEach(msg => {
        html += `<tr>
          <td>@${esc(msg.username || 'аноним')}</td>
          <td>${esc(msg.text)}</td>
          <td>${msg.date}</td>
          <td><button class="btn btn-accept" onclick="replyTo(${msg.chat_id})">✉️</button></td>
        </tr>`;
      });
      html += '</table>';
      container.innerHTML = html;
    } catch(e) {
      container.innerHTML = '<div class="empty">Ошибка загрузки сообщений.</div>';
    }
  }

  function replyTo(chatId) {
    const text = prompt('Введите ответ:');
    if (!text) return;
    fetch(`${API_BASE}/api/reply`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({chat_id: chatId, text, password: PASSWORD})
    }).then(r => r.json()).then(d => {
      if (d.status === 'ok') alert('✅ Ответ отправлен!');
      else alert('Ошибка: ' + (d.error || ''));
    });
  }

  window.onload = renderApps;
</script>
</body>
</html>"""

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

@app.route("/admin-panel")
def admin_panel_page():
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "Доступ запрещён. Укажите правильный пароль: ?pwd=...", 403
    return ADMIN_PANEL_HTML

@app.route("/api/applications")
def api_applications():
    if request.args.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    return jsonify(load_json(DATA_FILE, []))

@app.route("/api/accept", methods=["POST"])
def api_accept():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found or already processed"}), 404
    accept_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

@app.route("/api/reject", methods=["POST"])
def api_reject():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found or already processed"}), 404
    reject_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

@app.route("/api/messages")
def api_messages():
    if request.args.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    return jsonify(load_json(MESSAGES_FILE, []))

@app.route("/api/reply", methods=["POST"])
def api_reply():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    chat_id, text = data.get("chat_id"), data.get("text")
    if not chat_id or not text: return jsonify({"error": "chat_id и text обязательны"}), 400
    try:
        bot.send_message(chat_id, f"👑 Ответ от администрации:\n{text}")
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# ---------- TELEGRAM БОТ ----------
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

# ---------- ПЕРЕСЫЛКА ВХОДЯЩИХ СООБЩЕНИЙ (кроме команд) ----------
@bot.message_handler(func=lambda msg: not msg.text.startswith('/') and msg.chat.id not in ADMIN_IDS)
def forward_user_message(message):
    chat_id = message.chat.id
    username = message.chat.username or "аноним"
    text = message.text

    msgs = load_json(MESSAGES_FILE, [])
    msgs.append({
        "chat_id": chat_id,
        "username": username,
        "text": text,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_json(MESSAGES_FILE, msgs)

    for admin_id in ADMIN_IDS:
        try: bot.send_message(admin_id, f"💬 Сообщение от @{username} (ID {chat_id}):\n{text}")
        except: pass
    bot.send_message(chat_id, "✨ Твоё сообщение получено. Администратор скоро ответит.")

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
