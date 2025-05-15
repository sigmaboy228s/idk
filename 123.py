import telebot
from telebot import types
import json
import os
import time
from datetime import datetime, timedelta

TOKEN = '7940821929:AAGLU60CfIL17x0W9W00KlhWAbhkw'
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'certificates.json'
PHOTO_DIR = 'photos'
SPAM_DELAY = 2
last_message_time = {}

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'user_activity' not in data:
                    data['user_activity'] = {}
                return data
    except json.JSONDecodeError:
        print("Ошибка чтения файла данных, создан новый файл")
    
    return {
        'certificates': [],
        'certificate_details': {},
        'admins': [],
        'user_activity': {}
    }

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

def is_spamming(user_id):
    if str(user_id) in data['admins']:
        return False
    now = time.time()
    if user_id in last_message_time and (now - last_message_time[user_id]) < SPAM_DELAY:
        return True
    last_message_time[user_id] = now
    return False

user_states = {}

def clear_user_state(user_id):
    if user_id in user_states:
        del user_states[user_id]

cancel_kb = types.InlineKeyboardMarkup()
cancel_kb.add(types.InlineKeyboardButton("❌ СКАСУВАТИ", callback_data="cancel_action"))

data = load_data()
os.makedirs(PHOTO_DIR, exist_ok=True)

def is_admin(user_id):
    return str(user_id) in data['admins']

def get_bot_stats():
    total_users = len(data['user_activity'])
    day_counts = {}
    for user_days in data['user_activity'].values():
        for day in user_days:
            day_counts[day] = day_counts.get(day, 0) + 1
    if day_counts:
        average = sum(day_counts.values()) / len(day_counts)
    else:
        average = 0
    return total_users, round(average, 2)

@bot.message_handler(commands=['start'])
def start(message):
    if is_spamming(message.from_user.id):
        return
    
    clear_user_state(message.from_user.id)

    today = datetime.now().strftime('%Y-%m-%d')
    user_id_str = str(message.from_user.id)
    if user_id_str not in data['user_activity']:
        data['user_activity'][user_id_str] = []
    if today not in data['user_activity'][user_id_str]:
        data['user_activity'][user_id_str].append(today)
    save_data()

    text = "*👋 Привіт! Це магазин сувенірних посвідчень eBOSH Store 🪪 Підберемо щось для тебе?*"
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📋 МЕНЮ", callback_data="back_to_main"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=kb)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        if not message.text.startswith('/'):
            show_main_menu(message)
        return

@bot.callback_query_handler(func=lambda call: call.data == "cancel_action")
def cancel_action(call):
    user_id = call.from_user.id
    clear_user_state(user_id)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "❌ Операцію скасовано")
        msg = bot.send_message(call.message.chat.id, "⚙️ Налаштування")
        show_admin_panel(msg)
    except Exception as e:
        print(f"Помилка при обробці скасування: {e}")
        msg = bot.send_message(call.message.chat.id, "⚙️ Налаштування")
        show_admin_panel(msg)

def show_main_menu(message_or_call):
    kb = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("🪪 ПОСВІДЧЕННЯ", callback_data="certificates"),
        types.InlineKeyboardButton("📢 ВІДГУКИ", url="https://t.me/eBOSHfeedback"),
        types.InlineKeyboardButton("📞 ЗВ'ЯЗОК", callback_data="contact_menu")
    ]
    
    kb.add(*buttons[:2])
    kb.add(buttons[2])
    
    if hasattr(message_or_call, "data"):
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.message.chat.id
        message_id = message_or_call.message.message_id
    else:
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.chat.id
        message_id = None
    
    if is_admin(user_id):
        kb.add(types.InlineKeyboardButton("⚙️ НАЛАШТУВАННЯ", callback_data="admin"))
    
    try:
        if message_id:
            bot.edit_message_text("📋 ГОЛОВНЕ МЕНЮ:", chat_id, message_id, 
                                parse_mode='Markdown', reply_markup=kb)
        else:
            bot.send_message(chat_id, "📋 ГОЛОВНЕ МЕНЮ:", parse_mode='Markdown', reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні головного меню: {e}")
        bot.send_message(chat_id, "📋 ГОЛОВНЕ МЕНЮ:", parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "contact_menu")
def show_contact_menu(call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("👨‍💼 МЕНЕДЖЕР", url="https://t.me/mdjekson"))
    kb.add(types.InlineKeyboardButton("📷 INSTAGRAM", url="https://www.instagram.com/e.b.o.s.h?igsh=amFvMzNoeDcwc3Iz"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back_to_main"))
    
    try:
        bot.edit_message_text("📞 ЗВʼЯЗОК:", call.message.chat.id, call.message.message_id, 
                             reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні меню зв'язку: {e}")
        bot.send_message(call.message.chat.id, "📞 ЗВʼЯЗОК:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "certificates")
def show_cert_list(call):
    if is_spamming(call.from_user.id):
        return
    kb = types.InlineKeyboardMarkup()
    for cert in data.get('certificates', []):
        kb.add(types.InlineKeyboardButton(cert, callback_data=f"view_{cert}"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back_to_main"))
    
    try:
        bot.edit_message_text("Оберіть посвідчення:", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні списку посвідчень: {e}")
        bot.send_message(call.message.chat.id, "Оберіть посвідчення:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_cert(call):
    if is_spamming(call.from_user.id):
        return
    name = call.data.replace("view_", "")
    cert = data['certificate_details'].get(name)
    if not cert:
        bot.answer_callback_query(call.id, "Немає інформації.")
        return
    
    photo = cert.get('photo')
    if photo:
        photo_path = os.path.join(PHOTO_DIR, photo)
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo_file:
                bot.send_photo(call.message.chat.id, photo_file)

    text = f"{name}\n{cert['description']}"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛒 КУПИТИ", url="https://t.me/mdjekson"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="certificates"))
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "reviews")
def show_reviews(call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("ВІДГУКИ ↗", url="https://t.me/eBOSHfeedback"))
    bot.send_message(call.message.chat.id, "Натисніть кнопку нижче, щоб переглянути відгуки:", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin")
def show_admin_panel(call_or_message):
    if hasattr(call_or_message, 'data'):
        user_id = call_or_message.from_user.id
        chat_id = call_or_message.message.chat.id
        message_id = call_or_message.message.message_id
    else:
        user_id = call_or_message.from_user.id
        chat_id = call_or_message.chat.id
        message_id = None
        
    if not is_admin(user_id):
        if hasattr(call_or_message, 'data'):
            bot.answer_callback_query(call_or_message.id, "Немає доступу.")
        else:
            bot.send_message(chat_id, "Немає доступу.")
        return
    
    total_users, average_activity = get_bot_stats()
    stats_text = f"⚙️ НАЛАШТУВАННЯ\n\nСтатистика:\n👤 Users: {total_users}\n📊 Activity: {average_activity}"
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ ДОДАТИ", callback_data="add_cert"))
    kb.add(types.InlineKeyboardButton("➖ ВИДАЛИТИ", callback_data="del_cert"))
    kb.add(types.InlineKeyboardButton("✏️ РЕДАГУВАТИ", callback_data="edit_cert"))
    kb.add(types.InlineKeyboardButton("📤 РОЗСИЛКА", callback_data="broadcast"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back_to_main"))
    
    try:
        if message_id:
            bot.edit_message_text(stats_text, chat_id, message_id, reply_markup=kb)
        else:
            bot.send_message(chat_id, stats_text, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні панелі налаштувань: {e}")
        bot.send_message(chat_id, stats_text, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def start_broadcast(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        return
    user_states[user_id] = {'broadcast': {}}
    msg = bot.send_message(call.message.chat.id, "Введіть текст повідомлення для розсилки:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, process_broadcast_text)

def process_broadcast_text(message):
    user_id = message.from_user.id
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(user_id)
        bot.send_message(message.chat.id, "❌ Розсилку скасовано.")
        show_admin_panel(message)
        return
    
    user_states[user_id]['broadcast']['text'] = message.text
    msg = bot.send_message(message.chat.id, "📷 Надішліть фото (або натисніть ❌ СКАСУВАТИ):", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, process_broadcast_photo)

def process_broadcast_photo(message):
    user_id = message.from_user.id
    broadcast_data = user_states.get(user_id, {}).get('broadcast', {})

    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(user_id)
        bot.send_message(message.chat.id, "❌ Розсилку скасовано.")
        show_admin_panel(message)
        return
    
    if message.photo:
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            photo = bot.download_file(file_info.file_path)
            path = os.path.join(PHOTO_DIR, f"broadcast_{user_id}.jpg")
            with open(path, 'wb') as f:
                f.write(photo)
            broadcast_data['photo_path'] = path
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Помилка при завантаженні фото: {str(e)}")
            show_admin_panel(message)
            return
    
    text = broadcast_data['text']
    photo_path = broadcast_data.get('photo_path')

    delivered = 0
    failed = 0
    total_users = len(data['user_activity'])
    
    bot.send_message(message.chat.id, f"⏳ Початок розсилки для {total_users} користувачів...")
    
    for user_id_str in data['user_activity']:
        try:
            chat_id = int(user_id_str)
            if photo_path:
                with open(photo_path, 'rb') as p:
                    bot.send_photo(chat_id, p, caption=text)
            else:
                bot.send_message(chat_id, text)
            delivered += 1
            time.sleep(0.1)
        except Exception as e:
            failed += 1
            print(f"Помилка при відправці до {user_id_str}: {str(e)}")

    if photo_path and os.path.exists(photo_path):
        os.remove(photo_path)
    
    clear_user_state(user_id)
    summary = f"✅ Розсилку завершено!\n👥 Отримали: {delivered}\n❌ Не доставлено: {failed}"
    bot.send_message(message.chat.id, summary)
    show_admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "add_cert")
def add_cert_step1(call):
    bot.answer_callback_query(call.id)
    user_states[call.from_user.id] = "adding_cert"
    msg = bot.send_message(call.message.chat.id, "Введіть назву:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, add_cert_desc)

def add_cert_desc(message):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Додавання скасовано.")
        show_admin_panel(message)
        return
    
    name = message.text.strip()
    if not name:
        msg = bot.send_message(message.chat.id, "❌ Назва не може бути порожньою. Спробуйте ще раз:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, add_cert_desc)
        return
        
    if name in data['certificate_details']:
        msg = bot.send_message(message.chat.id, "❌ Така назва вже існує. Введіть іншу назву:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, add_cert_desc)
        return
    
    bot.send_message(message.chat.id, f"Введіть опис для '{name}':", reply_markup=cancel_kb)
    bot.register_next_step_handler(message, lambda m: add_cert_photo(m, name))

def add_cert_photo(message, name):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Додавання скасовано.")
        show_admin_panel(message)
        return
    
    desc = message.text.strip()
    if not desc:
        msg = bot.send_message(message.chat.id, "❌ Опис не може бути порожнім. Спробуйте ще раз:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, lambda m: add_cert_photo(m, name))
        return
    
    msg = bot.send_message(message.chat.id, "📷 Надішліть фото:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, lambda m: save_cert_photo(m, name, desc))

def save_cert_photo(message, name, desc):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Додавання скасовано.")
        show_admin_panel(message)
        return
    
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Будь ласка, надішліть фото.", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, lambda m: save_cert_photo(m, name, desc))
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        filename = f"{name}.jpg"
        path = os.path.join(PHOTO_DIR, filename)
        with open(path, 'wb') as f:
            f.write(downloaded)
        
        data['certificate_details'][name] = {'description': desc, 'photo': filename}
        data['certificates'].append(name)
        save_data()
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "✅ Успішно додано!")
        show_main_menu(message)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Помилка при збереженні фото: {str(e)}")
        show_admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "edit_cert")
def edit_cert_list(call):
    if is_spamming(call.from_user.id):
        return
    kb = types.InlineKeyboardMarkup()
    for cert in data['certificates']:
        kb.add(types.InlineKeyboardButton(cert, callback_data=f"select_edit_{cert}"))
    kb.add(types.InlineKeyboardButton("❌ СКАСУВАТИ", callback_data="cancel_edit_cert"))
    
    try:
        bot.edit_message_text("Оберіть для редагування:", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні списку для редагування: {e}")
        bot.send_message(call.message.chat.id, "Оберіть для редагування:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_edit_cert")
def cancel_edit_cert(call):
    bot.answer_callback_query(call.id, "❌ Редагування скасовано.")
    show_admin_panel(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_edit_"))
def edit_cert_options(call):
    name = call.data.replace("select_edit_", "")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📝 ЗМІНИТИ НАЗВУ", callback_data=f"edit_name_{name}"))
    kb.add(types.InlineKeyboardButton("✏️ ЗМІНИТИ ОПИС", callback_data=f"edit_desc_{name}"))
    kb.add(types.InlineKeyboardButton("🖼️ ЗМІНИТИ ФОТО", callback_data=f"edit_photo_{name}"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="edit_cert"))
    
    try:
        bot.edit_message_text(f"Редагування: {name}", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні опцій редагування: {e}")
        bot.send_message(call.message.chat.id, f"Редагування: {name}", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_name_"))
def edit_cert_name(call):
    name = call.data.replace("edit_name_", "")
    user_states[call.from_user.id] = {'editing': name, 'field': 'name'}
    msg = bot.send_message(call.message.chat.id, f"Введіть нову назву для {name}:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, save_edited_name)

def save_edited_name(message):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Редагування скасовано.")
        show_admin_panel(message)
        return
    
    user_data = user_states[message.from_user.id]
    old_name = user_data['editing']
    new_name = message.text.strip()
    
    if not new_name:
        msg = bot.send_message(message.chat.id, "❌ Назва не може бути порожньою. Спробуйте ще раз:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, save_edited_name)
        return
    
    if new_name in data['certificate_details'] and new_name != old_name:
        msg = bot.send_message(message.chat.id, "❌ Така назва вже існує. Введіть іншу назву:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, save_edited_name)
        return
    
    cert_data = data['certificate_details'][old_name]
    data['certificate_details'][new_name] = cert_data
    del data['certificate_details'][old_name]
    
    data['certificates'] = [new_name if c == old_name else c for c in data['certificates']]
    
    old_photo = cert_data.get('photo')
    if old_photo:
        old_photo_path = os.path.join(PHOTO_DIR, old_photo)
        new_photo_path = os.path.join(PHOTO_DIR, f"{new_name}.jpg")
        if os.path.exists(old_photo_path):
            os.rename(old_photo_path, new_photo_path)
        data['certificate_details'][new_name]['photo'] = f"{new_name}.jpg"
    
    save_data()
    clear_user_state(message.from_user.id)
    bot.send_message(message.chat.id, f"✅ Назву успішно змінено з '{old_name}' на '{new_name}'!")
    show_admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_desc_"))
def edit_cert_desc(call):
    name = call.data.replace("edit_desc_", "")
    user_states[call.from_user.id] = {'editing': name, 'field': 'description'}
    msg = bot.send_message(call.message.chat.id, f"Введіть новий опис для {name}:", rep
