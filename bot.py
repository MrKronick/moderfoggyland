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
ADMIN_APPS_FILE = "admin_applications.json"
PENDING_CODES_FILE = "pending_codes.json"
PORT = int(os.environ.get("PORT", 10000))
RENDER_URL = "https://moderfoggyland.onrender.com"   # ❗ Свой Render URL
ADMIN_PANEL_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Админ-панель FoggyLand</title>
  <style>
    body { font-family: 'Inter', sans-serif; background: #1a2e1a; color: #d0e6d5; padding: 2rem; }
    h1 { color: #9bc17a; }
    table { width: 100%; border-collapse: collapse; background: rgba(20,30,18,0.8); border-radius: 1rem; overflow: hidden; }
    th, td { padding: 0.8rem; border: 1px solid #2f4827; text-align: left; }
    th { background: #253d25; }
    .btn { border: none; padding: 0.5rem 1rem; border-radius: 0.5rem; cursor: pointer; font-weight: bold; }
    .accept { background: #2d8a3e; color: white; }
    .reject { background: #8a2d2d; color: white; }
    .hidden { display: none; }
    .details { background: #1e2e1e; padding: 1rem; margin-top: 0.5rem; border-radius: 0.5rem; }
    a { color: #9bc17a; }
  </style>
</head>
<body>
  <h1>👑 Админ-панель FoggyLand</h1>
  <p>Пароль для доступа: <strong>foggysecret</strong></p>
  <div id="apps-container">Загрузка...</div>

  <script>
    const PASSWORD = 'foggysecret';  // должен совпадать с ADMIN_PASSWORD
    const API_BASE = window.location.origin;

    async function loadApps() {
      try {
        const res = await fetch(`${API_BASE}/api/admin/applications?password=${PASSWORD}`);
        if (!res.ok) { document.getElementById('apps-container').innerHTML = 'Ошибка загрузки'; return; }
        const apps = await res.json();
        renderApps(apps);
      } catch(e) {
        document.getElementById('apps-container').innerHTML = 'Ошибка сети';
      }
    }

    function renderApps(apps) {
      if (apps.length === 0) {
        document.getElementById('apps-container').innerHTML = '<p>Заявок пока нет.</p>';
        return;
      }
      let html = '<table><tr><th>ID</th><th>Имя</th><th>Ник</th><th>TG</th><th>Статус</th><th>Действия</th></tr>';
      apps.forEach(app => {
        const status = app.status === 'accepted' ? '✅ Принята' : (app.status === 'rejected' ? '❌ Отклонена' : '⏳ Ожидает');
        html += `<tr>
          <td>${app.id}</td>
          <td>${app.full_name}</td>
          <td>${app.minecraft_nick}</td>
          <td>@${app.telegram_user || ''}</td>
          <td>${status}</td>
          <td>
            <button onclick="toggleDetails(${app.id})">📋 Детали</button>
            ${app.status === 'pending' ? `
              <button class="btn accept" onclick="handleAction(${app.id}, 'accept')">✅ Принять</button>
              <button class="btn reject" onclick="handleAction(${app.id}, 'reject')">❌ Отклонить</button>
            ` : ''}
          </td>
        </tr>`;
        html += `<tr id="details-${app.id}" class="hidden"><td colspan="6">
          <div class="details">
            <p><b>Возраст:</b> ${app.age || '-'}</p>
            <p><b>Часовой пояс:</b> ${app.timezone || '-'}</p>
            <p><b>Опыт на сервере:</b> ${app.modDuration || '-'}</p>
            <p><b>Активность:</b> ${app.modTasks || '-'}</p>
            <p><b>Готовность (часов/нед):</b> ${app.activityHours || '-'}</p>
            <p><b>Ответы на правила:</b></p>
            <ol>
              ${['rule_q1','rule_q2','rule_q3','rule_q4','rule_q5','rule_q6','rule_q7','rule_q8','rule_q9','rule_q10','rule_q11','rule_q12'].map(q => `<li>${app[q] || '—'}</li>`).join('')}
            </ol>
            <p><b>Технические навыки:</b> ${app.techSkills || '-'}</p>
            <p><b>Анализ логов:</b> ${app.logAnalysis || '-'}</p>
            <p><b>Управление командой:</b> ${app.teamManagement || '-'}</p>
            <p><b>Ситуации:</b></p>
            <ul>
              <li>Кража алмазов: ${app.situation1 || '-'}</li>
              <li>Скандал кланов: ${app.situation2 || '-'}</li>
              <li>Злоупотребление модера: ${app.situation3 || '-'}</li>
              <li>Популярный игрок: ${app.situation4 || '-'}</li>
            </ul>
            <p><b>Стиль наказаний:</b> ${app.punishmentStyle || '-'}</p>
            <p><b>Мотивация:</b> ${app.motivation || '-'}</p>
            <p><b>Предложения:</b> ${app.suggestions || '-'}</p>
            <p><b>Готовность уделять 15ч/нед:</b> ${app.commitment || '-'}</p>
          </div>
        </td></tr>`;
      });
      html += '</table>';
      document.getElementById('apps-container').innerHTML = html;
    }

    function toggleDetails(id) {
      const row = document.getElementById(`details-${id}`);
      if (row) row.classList.toggle('hidden');
    }

    async function handleAction(id, action) {
      if (!confirm(`Вы уверены, что хотите ${action === 'accept' ? 'принять' : 'отклонить'} заявку #${id}?`)) return;
      const url = `${API_BASE}/api/admin/${action}`;
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: id, password: PASSWORD })
        });
        const result = await res.json();
        if (res.ok) {
          alert(result.message || 'Готово');
          loadApps();
        } else {
          alert('Ошибка: ' + (result.error || 'неизвестно'));
        }
      } catch(e) {
        alert('Ошибка сети');
      }
    }

    loadApps();
  </script>
</body>
</html>
"""

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

# ----- Приём заявки на администратора (единственный маршрут) -----
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

    # Все остальные поля сохраняем как есть
    admin_apps = load_json(ADMIN_APPS_FILE, [])
    new_app = {
        "id": len(admin_apps) + 1,
        "chat_id": chat_id,
        "full_name": full_name,
        "minecraft_nick": nick,
        "telegram_user": tg,
        "age": data.get("age", ""),
        "timezone": data.get("timezone", ""),
        "modDuration": data.get("modDuration", ""),
        "modTasks": data.get("modTasks", ""),
        "activityHours": data.get("activityHours", ""),
        # Правила – можно сохранить все ответы
        "rule_q1": data.get("rule_q1", ""),
        "rule_q2": data.get("rule_q2", ""),
        "rule_q3": data.get("rule_q3", ""),
        "rule_q4": data.get("rule_q4", ""),
        "rule_q5": data.get("rule_q5", ""),
        "rule_q6": data.get("rule_q6", ""),
        "rule_q7": data.get("rule_q7", ""),
        "rule_q8": data.get("rule_q8", ""),
        "rule_q9": data.get("rule_q9", ""),
        "rule_q10": data.get("rule_q10", ""),
        "rule_q11": data.get("rule_q11", ""),
        "rule_q12": data.get("rule_q12", ""),
        "techSkills": data.get("techSkills", ""),
        "logAnalysis": data.get("logAnalysis", ""),
        "teamManagement": data.get("teamManagement", ""),
        "situation1": data.get("situation1", ""),
        "situation2": data.get("situation2", ""),
        "situation3": data.get("situation3", ""),
        "situation4": data.get("situation4", ""),
        "punishmentStyle": data.get("punishmentStyle", ""),
        "motivation": data.get("motivation", ""),
        "suggestions": data.get("suggestions", ""),
        "commitment": data.get("commitment", ""),
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }
    admin_apps.append(new_app)
    save_json(ADMIN_APPS_FILE, admin_apps)

    # Уведомление заявителю
    try:
        bot.send_message(chat_id,
                         f"Привет {full_name}! Твоя заявка на администратора принята и будет рассмотрена в течение 5-7 дней. Ожидай.")
    except Exception as e:
        print(f"Ошибка отправки заявителю: {e}")

    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id,
                             f"🆕 Заявка на администратора #{new_app['id']} от {full_name}\n"
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
        "• **🔑 Получить код** – выдаёт код для подачи заявки на администратора.\n"
        "• **ℹ️ Помощь** – эта подсказка.\n\n"
        "Правила сервера: https://rules.foggyland.ru\n"
        "По всем вопросам обращайтесь к администрации."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# Админ-панель (скрытая команда) – только для админов
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id not in ADMIN_IDS:
        bot.reply_to(message, "⛔ Нет доступа.")
        return
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("👑 Заявки на администратора", callback_data="list_admin_apps")
    )
    bot.send_message(message.chat.id, "🎛 Админ-панель FoggyLand", reply_markup=keyboard)

# ========== ОБРАБОТКА ЗАЯВОК (только админские) ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return

    data = call.data

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

    if data == "back_to_admin":
        admin_panel(call.message)
        return

# ========== ФУНКЦИИ ДЛЯ АДМИНСКИХ ЗАЯВОК ==========
def show_admin_list(call, apps):
    if not apps:
        bot.edit_message_text("📭 Заявок на администратора нет.", call.message.chat.id, call.message.message_id)
        return
    text = "👑 Заявки на администратора:\n\n"
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for a in apps[:10]:
        emoji = "✅" if a["status"] == "accepted" else "❌" if a["status"] == "rejected" else "⏳"
        text += f"{emoji} #{a['id']} | {a['full_name']} | {a['minecraft_nick']}\n"
        keyboard.add(types.InlineKeyboardButton(
            f"{emoji} #{a['id']} - {a['full_name']}",
            callback_data=f"admin_view_{a['id']}"
        ))
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def show_admin_detail(call, app):
    status = "✅ Принята" if app["status"] == "accepted" else "❌ Отклонена" if app["status"] == "rejected" else "⏳ Ожидает"
    text = (
        f"👑 Заявка #{app['id']}\n"
        f"👤 {app['full_name']}\n"
        f"⛏ Ник: {app['minecraft_nick']}\n"
        f"📬 Telegram: @{app.get('telegram_user','')}\n"
        f"📊 Статус: {status}\n\n"
        f"📅 Возраст: {app.get('age','—')}\n"
        f"🌍 Часовой пояс: {app.get('timezone','—')}\n"
        f"⏳ Опыт на сервере: {app.get('modDuration','—')}\n"
        f"💬 Мотивация: {app.get('motivation','—')}\n"
        f"📜 Правила: ответы сохранены (проверьте в файле)."
    )
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if app["status"] == "pending":
        keyboard.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"admin_accept_{app['id']}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_reject_{app['id']}")
        )
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="list_admin_apps"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)

def accept_admin_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "accepted"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}!\nТвоя заявка на администратора одобрена! Поздравляем!")
        bot.edit_message_text(f"✅ Заявка #{app_id} одобрена! Уведомление отправлено.", call.message.chat.id, call.message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 403:
            bot.edit_message_text(f"✅ Заявка #{app_id} одобрена!\n⚠️ Пользователь заблокировал бота — уведомление не доставлено.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

def reject_admin_app(call, app_id, apps):
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        bot.edit_message_text("❌ Заявка не найдена или уже обработана.", call.message.chat.id, call.message.message_id)
        return
    app["status"] = "rejected"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}. К сожалению, твоя заявка на администратора не прошла. Ты можешь подать повторно через 2 недели.")
        bot.edit_message_text(f"❌ Заявка #{app_id} отклонена! Уведомление отправлено.", call.message.chat.id, call.message.message_id)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 403:
            bot.edit_message_text(f"❌ Заявка #{app_id} отклонена!\n⚠️ Пользователь заблокировал бота — уведомление не доставлено.", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text(f"⚠️ Ошибка отправки: {e}", call.message.chat.id, call.message.message_id)
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {e}", call.message.chat.id, call.message.message_id)

# ========== ВЕБ-АДМИНКА ==========
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "foggysecret")  # смени пароль!

@app.route("/admin-panel")
def admin_panel_web():
    """Защищённая страница просмотра заявок"""
    pwd = request.args.get("pwd", "")
    if pwd != ADMIN_PASSWORD:
        return "Доступ запрещён. Укажите правильный пароль в URL: ?pwd=...", 403
    # Возвращаем HTML (он встроен ниже)
    return ADMIN_PANEL_HTML

# API для получения списка заявок (защищён паролем)
@app.route("/api/admin/applications")
def api_admin_applications():
    pwd = request.args.get("password", "")
    if pwd != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 401
    apps = load_json(ADMIN_APPS_FILE, [])
    return jsonify(apps)

# API для принятия заявки
@app.route("/api/admin/accept", methods=["POST"])
def api_admin_accept():
    data = request.get_json(force=True)
    pwd = data.get("password", "")
    if pwd != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(ADMIN_APPS_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        return jsonify({"error": "not found or already processed"}), 404
    app["status"] = "accepted"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}!\nТвоя заявка на администратора одобрена! Поздравляем!")
        return jsonify({"status": "ok", "message": "Уведомление отправлено"})
    except Exception as e:
        return jsonify({"status": "ok", "warning": f"Не удалось отправить уведомление: {e}"})

# API для отклонения заявки
@app.route("/api/admin/reject", methods=["POST"])
def api_admin_reject():
    data = request.get_json(force=True)
    pwd = data.get("password", "")
    if pwd != ADMIN_PASSWORD:
        return jsonify({"error": "unauthorized"}), 401
    app_id = data.get("id")
    apps = load_json(ADMIN_APPS_FILE, [])
    app = next((a for a in apps if a["id"] == app_id), None)
    if not app or app["status"] != "pending":
        return jsonify({"error": "not found or already processed"}), 404
    app["status"] = "rejected"
    save_json(ADMIN_APPS_FILE, apps)
    try:
        bot.send_message(app["chat_id"],
                         f"Привет {app['full_name']}. К сожалению, твоя заявка на администратора не прошла. Ты можешь подать повторно через 2 недели.")
        return jsonify({"status": "ok", "message": "Уведомление отправлено"})
    except Exception as e:
        return jsonify({"status": "ok", "warning": f"Не удалось отправить уведомление: {e}"})

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
