import os, json, uuid
from datetime import datetime
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
USER_MESSAGES_FILE = "user_messages.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
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

# ---------- ВСТРОЕННАЯ АДМИН-ПАНЕЛЬ ЗАЯВОК (HTML) ----------
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
  <div class="subtitle">Админ-панель заявок на мл. модератора</div>
  <div class="table-wrapper" id="table-container">
    <div class="loading">Загрузка заявок...</div>
  </div>
</div>

<!-- Модальное окно для деталей -->
<div class="modal" id="detailsModal">
  <div class="modal-content" id="modalContent"></div>
</div>

<script>
  const PASSWORD = 'foggy2026';
  const API_BASE = window.location.origin;

  async function fetchApps() {
    try {
      const res = await fetch(`${API_BASE}/api/applications?password=${PASSWORD}`);
      if (!res.ok) throw new Error('Ошибка доступа');
      return await res.json();
    } catch(e) {
      document.getElementById('table-container').innerHTML = '<div class="empty">❌ Ошибка загрузки</div>';
      return [];
    }
  }

  async function renderTable() {
    const apps = await fetchApps();
    const container = document.getElementById('table-container');
    if (!apps.length) {
      container.innerHTML = '<div class="empty">📭 Заявок пока нет</div>';
      return;
    }
    let html = `<table><thead><tr>
      <th>ID</th><th>Имя</th><th>Ник Minecraft</th><th>Telegram</th><th>Статус</th><th>Действия</th>
    </tr></thead><tbody>`;
    apps.forEach(app => {
      const statusClass = app.status === 'accepted' ? 'badge-accepted' : (app.status === 'rejected' ? 'badge-rejected' : 'badge-pending');
      const statusText = app.status === 'accepted' ? '✅ Принята' : (app.status === 'rejected' ? '❌ Отклонена' : '⏳ Ожидает');
      html += `<tr>
        <td>#${app.id}</td>
        <td>${escHtml(app.real_name)}</td>
        <td>${escHtml(app.minecraft_nick)}</td>
        <td>@${escHtml(app.telegram_user || '')}</td>
        <td><span class="badge ${statusClass}">${statusText}</span></td>
        <td>
          <button class="btn btn-details" onclick="showDetails(${app.id})">📋</button>
          ${app.status === 'pending' ? `
            <button class="btn btn-accept" onclick="act(${app.id},'accept')">✅</button>
            <button class="btn btn-reject" onclick="act(${app.id},'reject')">❌</button>
          ` : ''}
        </td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  }

  function escHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[m]);
  }

  async function act(id, action) {
    if (!confirm(`Точно ${action === 'accept' ? 'принять' : 'отклонить'} заявку #${id}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/${action}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id, password: PASSWORD})
      });
      const data = await res.json();
      if (res.ok) {
        alert('Готово!');
        renderTable();
      } else {
        alert('Ошибка: ' + (data.error || 'неизвестно'));
      }
    } catch(e) {
      alert('Сетевая ошибка');
    }
  }

  async function showDetails(id) {
    const apps = await fetchApps();
    const app = apps.find(a => a.id === id);
    if (!app) return;
    const content = document.getElementById('modalContent');
    content.innerHTML = `
      <button class="close-btn" onclick="closeModal()">✖</button>
      <h3>Заявка #${app.id}</h3>
      <p><b>Имя:</b> ${escHtml(app.real_name)}</p>
      <p><b>Ник:</b> ${escHtml(app.minecraft_nick)}</p>
      <p><b>Telegram:</b> @${escHtml(app.telegram_user || '')}</p>
      <p><b>Возраст:</b> ${escHtml(app.age || '')}</p>
      <p><b>Статус:</b> ${app.status === 'accepted' ? 'Принята' : (app.status === 'rejected' ? 'Отклонена' : 'Ожидает')}</p>
      <p><b>Опыт:</b> ${escHtml(app.experience || '—')}</p>
      <p><b>Мотивация:</b> ${escHtml(app.motivation || '—')}</p>
      <p><b>Согласие:</b> ${app.agreement === 'yes' ? 'Да' : 'Нет'}</p>
      <h4 style="margin-top:1rem;">📜 Ответы на правила</h4>
      <ol>
        <li>Читы (6.1): ${escHtml(app.rule_6_1 || '—')}</li>
        <li>Гриферство (8.1): ${escHtml(app.rule_8_1 || '—')}</li>
        <li>Оскорбления (2.1): ${escHtml(app.rule_2_1 || '—')}</li>
        <li>Администраторам (3.2): ${escHtml(app.rule_3_2 || '—')}</li>
        <li>Территория (9.3): ${escHtml(app.rule_9_3 || '—')}</li>
        <li>Спам/флуд (2.2-2.3): ${escHtml(app.rule_2_2_2_3 || '—')}</li>
        <li>Обход бана (8.5): ${escHtml(app.rule_8_5 || '—')}</li>
      </ol>
    `;
    document.getElementById('detailsModal').classList.add('active');
  }

  function closeModal() {
    document.getElementById('detailsModal').classList.remove('active');
  }

  window.onload = renderTable;
</script>
</body>
</html>"""

# ---------- ВСТРОЕННЫЙ ЧАТ-ИНТЕРФЕЙС (HTML) ----------
CHAT_PANEL_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>FoggyLand Chat Admin</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family: 'Inter', sans-serif;
      background: radial-gradient(circle at 20% 30%, #1f3b1f, #0a1a0a);
      min-height:100vh; padding:1rem; color:#d0e6d5;
    }
    .container { max-width:900px; margin:0 auto; }
    h1 {
      font-size:2.2rem; font-weight:800;
      background: linear-gradient(180deg, #d4f0c0, #7fa86b);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      text-align:center; margin-bottom:1rem;
    }
    .chat-box {
      background: rgba(10,20,12,0.8); backdrop-filter: blur(20px);
      border-radius:1.5rem; padding:1.5rem; border:1px solid rgba(120,170,80,0.3);
      margin-bottom:1rem;
    }
    .messages {
      max-height: 50vh; overflow-y: auto; margin-bottom:1rem;
    }
    .msg {
      padding:0.6rem 1rem; margin-bottom:0.5rem; border-radius:1rem;
      background: rgba(30,50,30,0.6); word-break:break-word;
    }
    .msg.admin { background: rgba(60,100,40,0.6); }
    .msg small { color:#8aa87c; font-size:0.8rem; display:block; }
    .input-area { display:flex; gap:0.5rem; }
    input[type="text"] {
      flex:1; padding:0.7rem 1rem; background: rgba(8,15,8,0.7);
      border:1.5px solid #3b5432; border-radius:1.2rem; color:#eaf4e0;
      font-size:1rem; outline:none;
    }
    button {
      padding:0.7rem 1.5rem; background: #2b5322; color:#f2ffe5;
      border:none; border-radius:1.2rem; font-weight:600; cursor:pointer;
      transition:0.2s;
    }
    button:hover { background: #3d7330; }
    .user-list { display:flex; flex-direction:column; gap:0.3rem; margin-bottom:1rem; }
    .user-item {
      background: rgba(20,30,18,0.7); padding:0.8rem 1rem; border-radius:1rem;
      cursor:pointer; border:1px solid rgba(90,150,100,0.3);
      transition:0.2s;
    }
    .user-item:hover { background: rgba(40,70,40,0.7); }
    .back-link { color:#9bc17a; text-decoration:none; margin-bottom:1rem; display:inline-block; }
  </style>
</head>
<body>
<div class="container">
  <h1>💬 Чат с пользователями</h1>
  <a class="back-link" href="/admin-panel?pwd=foggy2026">← К заявкам</a>
  <div id="chat-container">
    <div class="user-list" id="user-list"></div>
    <div id="conversation" class="chat-box" style="display:none;"></div>
  </div>
</div>

<script>
  const PASSWORD = 'foggy2026';
  const API_BASE = window.location.origin;
  let currentChatId = null;

  async function fetchUsers() {
    try {
      const res = await fetch(`${API_BASE}/api/chat/users?password=${PASSWORD}`);
      if (!res.ok) throw new Error('Ошибка');
      return await res.json();
    } catch(e) {
      document.getElementById('user-list').innerHTML = '<p>Ошибка загрузки</p>';
      return [];
    }
  }

  async function fetchMessages(chatId) {
    const res = await fetch(`${API_BASE}/api/chat/messages?password=${PASSWORD}&chat_id=${chatId}`);
    if (!res.ok) return [];
    return await res.json();
  }

  function renderUserList(users) {
    const container = document.getElementById('user-list');
    if (!users.length) {
      container.innerHTML = '<p>Нет сообщений от пользователей.</p>';
      return;
    }
    container.innerHTML = users.map(u => `
      <div class="user-item" onclick="openChat(${u.chat_id})">
        <strong>@${u.username}</strong> (ID: ${u.chat_id})<br>
        <small>Последнее: ${u.last_text || ''}</small>
      </div>
    `).join('');
  }

  async function openChat(chatId) {
    currentChatId = chatId;
    const msgs = await fetchMessages(chatId);
    const convDiv = document.getElementById('conversation');
    convDiv.style.display = 'block';
    let html = '<div class="messages">';
    msgs.forEach(m => {
      const cls = m.from_admin ? 'admin' : '';
      html += `<div class="msg ${cls}">
        <small>@${m.username} | ${new Date(m.timestamp).toLocaleString('ru')}</small>
        ${escapeHtml(m.text)}
      </div>`;
    });
    html += '</div>';
    html += `
      <div class="input-area">
        <input type="text" id="replyInput" placeholder="Напишите ответ...">
        <button onclick="sendReply()">Отправить</button>
      </div>`;
    convDiv.innerHTML = html;
  }

  async function sendReply() {
    const text = document.getElementById('replyInput').value.trim();
    if (!text || !currentChatId) return;
    try {
      const res = await fetch(`${API_BASE}/api/chat/reply`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ chat_id: currentChatId, text, password: PASSWORD })
      });
      const data = await res.json();
      if (res.ok) {
        document.getElementById('replyInput').value = '';
        openChat(currentChatId);
      } else {
        alert('Ошибка: ' + (data.error || 'неизвестно'));
      }
    } catch(e) {
      alert('Сетевая ошибка');
    }
  }

  function escapeHtml(text) {
    return text.replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[m]);
  }

  (async () => {
    const users = await fetchUsers();
    renderUserList(users);
  })();
</script>
</body>
</html>"""

# ---------- МАРШРУТЫ FLASK ----------
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

# ---------- МАРШРУТЫ АДМИН-ПАНЕЛИ ЗАЯВОК ----------
@app.route("/admin-panel")
def admin_panel_page():
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "Доступ запрещён. Укажите правильный пароль: ?pwd=...", 403
    return ADMIN_PANEL_HTML

@app.route("/api/applications")
def api_applications():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 401
    apps = load_json(DATA_FILE, [])
    return jsonify(apps)

@app.route("/api/accept", methods=["POST"])
def api_accept():
    data = request.get_json(force=True)
    pwd = data.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found or already processed"}), 404
    accept_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

@app.route("/api/reject", methods=["POST"])
def api_reject():
    data = request.get_json(force=True)
    pwd = data.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(DATA_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending": return jsonify({"error": "not found or already processed"}), 404
    reject_ml_app_web(app, apps)
    return jsonify({"status": "ok"})

# ---------- МАРШРУТЫ ЧАТА ----------
@app.route("/admin-chat")
def admin_chat_page():
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "Доступ запрещён. Укажите правильный пароль: ?pwd=...", 403
    return CHAT_PANEL_HTML

@app.route("/api/chat/users")
def api_chat_users():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    msgs = load_json(USER_MESSAGES_FILE, [])
    users = {}
    for m in msgs:
        if m["from_admin"]: continue
        cid = m["chat_id"]
        if cid not in users or m["timestamp"] > users[cid]["timestamp"]:
            users[cid] = {
                "chat_id": cid,
                "username": m["username"],
                "last_text": m["text"],
                "timestamp": m["timestamp"]
            }
    return jsonify(list(users.values()))

@app.route("/api/chat/messages")
def api_chat_messages():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    try:
        chat_id = int(request.args.get("chat_id"))
    except:
        return jsonify({"error": "invalid chat_id"}), 400
    msgs = load_json(USER_MESSAGES_FILE, [])
    user_msgs = [m for m in msgs if m["chat_id"] == chat_id]
    return jsonify(user_msgs)

@app.route("/api/chat/reply", methods=["POST"])
def api_chat_reply():
    data = request.get_json(force=True)
    pwd = data.get("password", "")
    if pwd != ADMIN_PASSWORD: return jsonify({"error": "unauthorized"}), 401
    try:
        target_id = int(data.get("chat_id"))
    except:
        return jsonify({"error": "invalid chat_id"}), 400
    text = data.get("text", "").strip()
    if not text: return jsonify({"error": "empty text"}), 400
    try:
        bot.send_message(target_id, text)
        save_message(target_id, "admin", text, from_admin=True)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ЗАЯВОК ----------
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

# ---------- ЖИВАЯ ПОДДЕРЖКА (TELEGRAM) ----------
def save_message(chat_id, username, text, from_admin=False):
    msgs = load_json(USER_MESSAGES_FILE, [])
    msgs.append({
        "chat_id": chat_id,
        "username": username,
        "text": text,
        "from_admin": from_admin,
        "timestamp": datetime.now().isoformat()
    })
    save_json(USER_MESSAGES_FILE, msgs)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    if message.text.startswith('/'): return
    chat_id = message.chat.id
    if chat_id in ADMIN_IDS: return
    user = message.chat.username or "аноним"
    text = message.text
    save_message(chat_id, user, text)
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, f"📩 Сообщение от @{user} (ID: `{chat_id}`):\n{text}", parse_mode="Markdown")
        except: pass

@bot.message_handler(commands=['reply'])
def reply_to_user(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа."); return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.reply_to(message, "Использование: /reply <chat_id> <текст>"); return
    try:
        target_id = int(args[1])
    except ValueError:
        bot.reply_to(message, "Неверный chat_id."); return
    reply_text = args[2]
    try:
        bot.send_message(target_id, reply_text)
        bot.reply_to(message, f"✅ Ответ отправлен пользователю {target_id}.")
        save_message(target_id, "admin", reply_text, from_admin=True)
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при отправке: {e}")

@bot.message_handler(commands=['history'])
def user_history(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа."); return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Использование: /history <chat_id>"); return
    try:
        user_id = int(args[1])
    except ValueError:
        bot.reply_to(message, "Неверный chat_id."); return
    msgs = load_json(USER_MESSAGES_FILE, [])
    user_msgs = [m for m in msgs if m["chat_id"] == user_id][-10:]
    if not user_msgs:
        bot.reply_to(message, "Нет сохранённых сообщений с этим пользователем.")
        return
    text = f"📜 Последние сообщения от/для `{user_id}`:\n\n"
    for m in user_msgs:
        prefix = "🟢" if m["from_admin"] else "🔵"
        text += f"{prefix} @{m['username']}: {m['text']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ---------- TELEGRAM БОТ (ОСНОВНЫЕ КОМАНДЫ) ----------
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
    print("[START] Бот запущен. Админ-панель, чат и поддержка включены.")
    app.run(host="0.0.0.0", port=PORT)
