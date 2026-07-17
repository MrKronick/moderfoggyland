import os, json, uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
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
MESSAGES_FILE = "user_messages.json"  # храним входящие сообщения
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

# ---------- ВСТРОЕННАЯ АДМИН-ПАНЕЛЬ (с чатом) ----------
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
    .container { max-width: 1100px; margin: 0 auto; position: relative; z-index: 2; }
    h1 {
      font-size: 2.8rem; font-weight: 800;
      background: linear-gradient(180deg, #d4f0c0, #7fa86b);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      text-align: center; margin-bottom: 0.5rem;
    }
    .tabs {
      display: flex; gap: 0.5rem; margin-bottom: 2rem; justify-content: center; flex-wrap: wrap;
    }
    .tab {
      padding: 0.7rem 1.8rem; border-radius: 2rem; background: rgba(20,30,18,0.6);
      backdrop-filter: blur(10px); border: 1px solid #5e874b; color: #bcddb0;
      cursor: pointer; font-weight: 600; transition: 0.2s;
    }
    .tab.active { background: #2d6a2d; border-color: #7cc96b; color: white; }
    .tab:hover:not(.active) { background: rgba(60,90,40,0.7); }
    .panel { display: none; }
    .panel.active { display: block; }

    .table-wrapper {
      background: rgba(10,20,12,0.7); backdrop-filter: blur(20px);
      border-radius: 2rem; padding: 1.5rem;
      box-shadow: 0 30px 50px -20px rgba(0,0,0,0.7), 0 0 0 1px rgba(100,150,90,0.4);
      border: 1px solid rgba(120,170,80,0.3); overflow-x: auto;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
    th, td { padding: 0.9rem 1rem; text-align: left; border-bottom: 1px solid rgba(90,150,100,0.25); }
    th { background: rgba(30,50,30,0.6); color: #c0e0b0; }
    tr:hover td { background: rgba(60,90,40,0.3); }
    .badge { padding: 0.3rem 0.8rem; border-radius: 2rem; font-weight: 600; font-size: 0.85rem; }
    .badge-pending { background: #5a5a30; color: #ffffb0; }
    .badge-accepted { background: #2d6a2d; color: #c0ffc0; }
    .badge-rejected { background: #6a2d2d; color: #ffc0c0; }
    .btn {
      padding: 0.5rem 1.2rem; border: none; border-radius: 1.2rem;
      font-weight: 600; cursor: pointer; transition: 0.2s; font-size: 0.85rem; margin: 0.2rem;
    }
    .btn-accept { background: #2d6a2d; color: white; }
    .btn-accept:hover { background: #3e8e3e; }
    .btn-reject { background: #6a2d2d; color: white; }
    .btn-reject:hover { background: #8e3e3e; }
    .btn-details { background: rgba(80,130,60,0.3); color: #c0e0b0; }
    .btn-details:hover { background: rgba(80,130,60,0.5); }

    /* Чат */
    .chat-container {
      display: flex; gap: 1rem; height: 70vh; min-height: 500px;
    }
    .user-list {
      width: 280px; background: rgba(10,20,12,0.8); backdrop-filter: blur(20px);
      border-radius: 1.5rem; padding: 1rem; overflow-y: auto;
      border: 1px solid #5e874b;
    }
    .user-item {
      padding: 0.8rem 1rem; border-radius: 1rem; cursor: pointer;
      border: 1px solid transparent; margin-bottom: 0.5rem; transition: 0.2s;
    }
    .user-item:hover, .user-item.active { background: rgba(80,150,80,0.3); border-color: #7cc96b; }
    .user-item .name { font-weight: 600; }
    .user-item .last-msg { font-size: 0.8rem; color: #a0c090; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .chat-window {
      flex: 1; display: flex; flex-direction: column;
      background: rgba(10,20,12,0.8); backdrop-filter: blur(20px);
      border-radius: 1.5rem; border: 1px solid #5e874b; overflow: hidden;
    }
    .chat-header {
      padding: 1rem; background: rgba(30,50,30,0.6); font-weight: 600;
      border-bottom: 1px solid #5e874b;
    }
    .chat-messages {
      flex: 1; padding: 1rem; overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem;
    }
    .msg {
      max-width: 80%; padding: 0.7rem 1rem; border-radius: 1.2rem; word-break: break-word;
    }
    .msg.user { align-self: flex-start; background: #2d5a2d; }
    .msg.admin { align-self: flex-end; background: #2d4a6a; }
    .msg .time { font-size: 0.7rem; color: #a0c090; margin-top: 0.3rem; }
    .chat-input {
      padding: 0.8rem; background: rgba(20,30,18,0.8); display: flex; gap: 0.5rem;
      border-top: 1px solid #5e874b;
    }
    .chat-input input { flex: 1; padding: 0.6rem 1rem; border-radius: 2rem; border: 1px solid #5e874b;
      background: rgba(0,0,0,0.3); color: #e0f0d0; outline: none; }
    .chat-input button { padding: 0.6rem 1.5rem; border-radius: 2rem; border: none;
      background: #2d6a2d; color: white; font-weight: 600; cursor: pointer; }
    .chat-input button:hover { background: #3e8e3e; }
    .empty-chat { color: #80a070; text-align: center; margin-top: 2rem; }

    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.7); backdrop-filter: blur(10px); z-index: 1000;
      justify-content: center; align-items: center; }
    .modal.active { display: flex; }
    .modal-content { background: rgba(20,30,18,0.95); backdrop-filter: blur(25px);
      border: 1px solid #5e874b; border-radius: 2rem; padding: 2rem;
      max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; }
    .close-btn { float: right; background: none; border: none; color: #a0c090; font-size: 1.5rem; cursor: pointer; }
  </style>
</head>
<body>
<div class="container">
  <h1>👑 FoggyLand</h1>
  <div class="tabs">
    <div class="tab active" onclick="switchTab('applications')">📋 Заявки</div>
    <div class="tab" onclick="switchTab('messages')">💬 Сообщения</div>
  </div>

  <!-- Панель заявок -->
  <div id="panel-applications" class="panel active">
    <div class="table-wrapper" id="table-container">
      <div class="loading">Загрузка...</div>
    </div>
  </div>

  <!-- Панель сообщений -->
  <div id="panel-messages" class="panel">
    <div class="chat-container">
      <div class="user-list" id="userList">Загрузка...</div>
      <div class="chat-window" id="chatWindow">
        <div class="chat-header" id="chatHeader">Выберите пользователя</div>
        <div class="chat-messages" id="chatMessages">
          <div class="empty-chat">👈 Выберите пользователя слева</div>
        </div>
        <div class="chat-input" id="chatInput" style="display:none;">
          <input type="text" id="msgInput" placeholder="Введите сообщение..." onkeypress="if(event.key==='Enter') sendMessage()">
          <button onclick="sendMessage()">Отправить</button>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="modal" id="detailsModal"><div class="modal-content" id="modalContent"></div></div>

<script>
  const PASSWORD = 'foggy2026';
  const API_BASE = window.location.origin;
  let activeChatId = null;

  // Переключение вкладок
  function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    event.target.classList.add('active');
    document.getElementById('panel-' + tab).classList.add('active');
    if (tab === 'messages') loadUsers();
  }

  // ========== ЗАЯВКИ ==========
  async function fetchApps() {
    try {
      const res = await fetch(`${API_BASE}/api/applications?password=${PASSWORD}`);
      if (!res.ok) throw new Error('Ошибка');
      return await res.json();
    } catch(e) {
      document.getElementById('table-container').innerHTML = '<div class="empty">❌ Ошибка</div>';
      return [];
    }
  }

  async function renderTable() {
    const apps = await fetchApps();
    const container = document.getElementById('table-container');
    if (!apps.length) { container.innerHTML = '<div class="empty">📭 Заявок нет</div>'; return; }
    let html = `<table><thead><tr><th>ID</th><th>Имя</th><th>Ник</th><th>TG</th><th>Статус</th><th>Действия</th></tr></thead><tbody>`;
    apps.forEach(app => {
      const sc = app.status === 'accepted' ? 'badge-accepted' : (app.status === 'rejected' ? 'badge-rejected' : 'badge-pending');
      const st = app.status === 'accepted' ? '✅ Принята' : (app.status === 'rejected' ? '❌ Отклонена' : '⏳ Ожидает');
      html += `<tr>
        <td>#${app.id}</td><td>${esc(app.real_name)}</td><td>${esc(app.minecraft_nick)}</td>
        <td>@${esc(app.telegram_user||'')}</td><td><span class="badge ${sc}">${st}</span></td>
        <td>
          <button class="btn btn-details" onclick="showDetails(${app.id})">📋</button>
          ${app.status==='pending' ? `<button class="btn btn-accept" onclick="act(${app.id},'accept')">✅</button>
          <button class="btn btn-reject" onclick="act(${app.id},'reject')">❌</button>` : ''}
        </td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  async function act(id, action) {
    if (!confirm(`Точно ${action==='accept'?'принять':'отклонить'} заявку #${id}?`)) return;
    const res = await fetch(`${API_BASE}/api/${action}`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id, password: PASSWORD})
    });
    if (res.ok) { alert('Готово!'); renderTable(); }
    else { const d = await res.json(); alert('Ошибка: '+(d.error||'')); }
  }

  async function showDetails(id) {
    const apps = await fetchApps(); const app = apps.find(a => a.id===id); if(!app) return;
    document.getElementById('modalContent').innerHTML = `
      <button class="close-btn" onclick="document.getElementById('detailsModal').classList.remove('active')">✖</button>
      <h3>Заявка #${app.id}</h3>
      <p><b>Имя:</b> ${esc(app.real_name)}</p>
      <p><b>Ник:</b> ${esc(app.minecraft_nick)}</p>
      <p><b>TG:</b> @${esc(app.telegram_user||'')}</p>
      <p><b>Возраст:</b> ${esc(app.age||'')}</p>
      <p><b>Статус:</b> ${app.status==='accepted'?'Принята':(app.status==='rejected'?'Отклонена':'Ожидает')}</p>
      <p><b>Опыт:</b> ${esc(app.experience||'—')}</p>
      <p><b>Мотивация:</b> ${esc(app.motivation||'—')}</p>
      <h4>📜 Ответы</h4><ol>
        <li>Читы: ${esc(app.rule_6_1||'—')}</li>
        <li>Гриф: ${esc(app.rule_8_1||'—')}</li>
        <li>Оскорбления: ${esc(app.rule_2_1||'—')}</li>
        <li>Админам: ${esc(app.rule_3_2||'—')}</li>
        <li>Территория: ${esc(app.rule_9_3||'—')}</li>
        <li>Спам/флуд: ${esc(app.rule_2_2_2_3||'—')}</li>
        <li>Обход бана: ${esc(app.rule_8_5||'—')}</li>
      </ol>`;
    document.getElementById('detailsModal').classList.add('active');
  }

  function esc(t){ return t?t.replace(/[&<>"]/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[m]):''; }

  // ========== СООБЩЕНИЯ ==========
  async function loadUsers() {
    const res = await fetch(`${API_BASE}/api/recent-messages?password=${PASSWORD}`);
    const users = await res.json();
    const list = document.getElementById('userList');
    if (!users.length) { list.innerHTML = '<div style="color:#80a070;padding:1rem;">Нет сообщений</div>'; return; }
    list.innerHTML = users.map(u => `
      <div class="user-item" onclick="openChat(${u.chat_id})">
        <div class="name">${esc(u.name||'Пользователь')} (ID: ${u.chat_id})</div>
        <div class="last-msg">${esc(u.last_msg||'')}</div>
      </div>
    `).join('');
  }

  async function openChat(chatId) {
    activeChatId = chatId;
    document.querySelectorAll('.user-item').forEach(el => el.classList.remove('active'));
    event.target.closest('.user-item').classList.add('active');

    const res = await fetch(`${API_BASE}/api/messages/${chatId}?password=${PASSWORD}`);
    const msgs = await res.json();
    const header = document.getElementById('chatHeader');
    const msgsDiv = document.getElementById('chatMessages');
    const inputDiv = document.getElementById('chatInput');

    header.textContent = `Чат с ${msgs[0]?.from_name || 'пользователем'} (ID: ${chatId})`;
    inputDiv.style.display = 'flex';

    if (!msgs.length) { msgsDiv.innerHTML = '<div class="empty-chat">Нет сообщений</div>'; return; }
    msgsDiv.innerHTML = msgs.map(m => `
      <div class="msg ${m.from==='admin'?'admin':'user'}">
        ${esc(m.text)}<div class="time">${m.time||''}</div>
      </div>
    `).join('');
    msgsDiv.scrollTop = msgsDiv.scrollHeight;
  }

  async function sendMessage() {
    const input = document.getElementById('msgInput');
    const text = input.value.trim();
    if (!text || !activeChatId) return;
    const res = await fetch(`${API_BASE}/api/send-message`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({chat_id: activeChatId, text, password: PASSWORD})
    });
    if (res.ok) {
      input.value = '';
      openChat(activeChatId); // обновим чат
    } else {
      alert('Ошибка отправки');
    }
  }

  window.onload = renderTable;
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
    if pwd != ADMIN_PASSWORD: return "Доступ запрещён", 403
    return ADMIN_PANEL_HTML

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

def accept_ml_app_web(app, apps):
    app["status"] = "accepted"
    chat_id, user_nick = app["chat_id"], app.get("minecraft_nick", "игрок")
    pending_tags = load_json(PENDING_TAGS_FILE, [])
    pending_tags.append({"chat_id": chat_id, "nick": user_nick})
    save_json(PENDING_TAGS_FILE, pending_tags)
    try:
        bot.add_chat_member(chat_id=STAFF_GROUP_ID, user_id=chat_id)
        bot.send_message(chat_id, "✅ Ты добавлен в группу модераторов! Тег будет выдан автоматически.")
        bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** присоединился!", parse_mode="Markdown")
    except:
        try:
            invite = bot.create_chat_invite_link(chat_id=STAFF_GROUP_ID, member_limit=1, name=f"Приглашение для {user_nick}")
            bot.send_message(chat_id, f"🎉 Поздравляю, {app['real_name']}!\n\nТвоя заявка одобрена!\nПерейди по ссылке для входа в группу:\n\n🔗 {invite.invite_link}\n\nПосле входа тебе автоматически выдадут тег.", disable_web_page_preview=True)
            bot.send_message(STAFF_GROUP_ID, f"👋 Новый мл. модератор **{user_nick}** скоро присоединится.", parse_mode="Markdown")
        except: bot.send_message(chat_id, "⚠️ Не удалось добавить в группу. Администратор добавит вас вручную.")
    save_json(DATA_FILE, apps)

def reject_ml_app_web(app, apps):
    app["status"] = "rejected"
    save_json(DATA_FILE, apps)
    try: bot.send_message(app["chat_id"], f"Привет {app['real_name']}. К сожалению, твоя заявка не прошла. Можешь подать повторно через 7 дней.")
    except: pass

# ---------- API ЧАТА ----------
@app.route("/api/recent-messages")
def api_recent_messages():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    msgs = load_json(MESSAGES_FILE, [])
    # группируем по chat_id, берём последнее сообщение
    users = {}
    for m in msgs:
        cid = m["chat_id"]
        if cid not in users or m["time"] > users[cid]["last_time"]:
            users[cid] = {"chat_id": cid, "name": m.get("from_name", ""), "last_msg": m["text"], "last_time": m["time"]}
    return jsonify(list(users.values()))

@app.route("/api/messages/<int:chat_id>")
def api_messages(chat_id):
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    msgs = load_json(MESSAGES_FILE, [])
    chat_msgs = [m for m in msgs if m["chat_id"] == chat_id]
    return jsonify(chat_msgs)

@app.route("/api/send-message", methods=["POST"])
def api_send_message():
    data = request.get_json(force=True)
    if data.get("password") != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    chat_id = data.get("chat_id")
    text = data.get("text")
    if not chat_id or not text: return jsonify({"error": "missing params"}), 400
    try:
        sent = bot.send_message(chat_id, text)
        # сохраняем в историю
        msgs = load_json(MESSAGES_FILE, [])
        msgs.append({
            "chat_id": chat_id,
            "from": "admin",
            "from_name": "Администратор",
            "text": text,
            "time": datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        save_json(MESSAGES_FILE, msgs)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# Обработчик всех текстовых сообщений (сохраняем в историю)
@bot.message_handler(func=lambda msg: True, content_types=['text'])
def catch_all_messages(message):
    if message.chat.id in ADMIN_IDS: return  # не сохраняем сообщения админов
    msgs = load_json(MESSAGES_FILE, [])
    msgs.append({
        "chat_id": message.chat.id,
        "from": "user",
        "from_name": message.chat.first_name or "Пользователь",
        "text": message.text,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_json(MESSAGES_FILE, msgs)
    # Отвечаем стандартным сообщением, если это не команда
    if not message.text.startswith('/'):
        bot.reply_to(message, "📩 Ваше сообщение получено. Администратор скоро ответит.")

# Остальные старые обработчики (admin, сменитьтег, new_chat_members, callback) – оставлены без изменений
# (вставьте их сюда из предыдущего кода)

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    bot.set_webhook(url=f"{RENDER_URL}/telegram")
    app.run(host="0.0.0.0", port=PORT)
