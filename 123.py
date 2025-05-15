import telebot
from telebot import types
import json
import os
import time

TOKEN = 'x'
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'certificates.json'
PHOTO_DIR = 'photos'
SPAM_DELAY = 2
last_message_time = {}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'certificates': [], 'certificate_details': {}, 'admins': []}

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_spamming(user_id):
    if str(user_id) in data['admins']:
        return False
    now = time.time()
    if user_id in last_message_time and (now - last_message_time[user_id]) < SPAM_DELAY:
        return True
    last_message_time[user_id] = now
    return False

# User state management
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

@bot.message_handler(commands=['start'])
def start(message):
    if is_spamming(message.from_user.id):
        return
    
    clear_user_state(message.from_user.id)
    text = "👋 Привіт! Це магазин сувенірних посвідчень *eBOSH Store*. Підберемо щось для тебе?"
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
        # Отправляем новое сообщение вместо редактирования
        msg = bot.send_message(call.message.chat.id, "🔧 Адмін-панель")
        show_admin_panel(msg)
    except Exception as e:
        print(f"Помилка при обробці скасування: {e}")
        # Отправляем новое сообщение в любом случае
        msg = bot.send_message(call.message.chat.id, "🔧 Адмін-панель")
        show_admin_panel(msg)

def show_main_menu(message_or_call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🪪 ПОСВІДЧЕННЯ", callback_data="certificates"))
    kb.add(types.InlineKeyboardButton("📢 ВІДГУКИ", url="https://t.me/eBOSHfeedback"))
    
    # Get user_id and chat_id from either message or callback query
    if hasattr(message_or_call, "data"):  # It's a callback query
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.message.chat.id
        message_id = message_or_call.message.message_id
    else:  # It's a message
        user_id = message_or_call.from_user.id
        chat_id = message_or_call.chat.id
        message_id = None
    
    if is_admin(user_id):
        kb.add(types.InlineKeyboardButton("⚙️ АДМІН-ПАНЕЛЬ", callback_data="admin"))
    
    try:
        # Check if it's a callback query or a message
        if message_id:  # It's a callback query
            bot.edit_message_text("📋 Головне меню:", chat_id, message_id, 
                                parse_mode='Markdown', reply_markup=kb)
        else:  # It's a message
            bot.send_message(chat_id, "📋 Головне меню:", parse_mode='Markdown', reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні головного меню: {e}")
        bot.send_message(chat_id, "📋 Головне меню:", parse_mode='Markdown', reply_markup=kb)

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
    if photo and os.path.exists(photo):
        bot.send_photo(call.message.chat.id, open(photo, 'rb'))

    text = (
        f"🔹 Назва: {name}\n"
        f"📄 Опис: {cert['description']}\n"
        f"💵 Ціна: {cert.get('price', 'Не вказано')}"
    )
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🛒 КУПИТИ", url="https://t.me/mdjekson"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД ДО ГОЛОВНОГО", callback_data="back_to_main"))
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "reviews")
def show_reviews(call):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("ВІДГУКИ ↗", url="https://t.me/eBOSHfeedback"))
    bot.send_message(call.message.chat.id, "Натисніть кнопку нижче, щоб переглянути відгуки:", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin")
def show_admin_panel(call_or_message):
    # Получаем ID пользователя и чата
    if hasattr(call_or_message, 'data'):  # Это CallbackQuery
        user_id = call_or_message.from_user.id
        chat_id = call_or_message.message.chat.id
        message_id = call_or_message.message.message_id
    else:  # Это Message
        user_id = call_or_message.from_user.id
        chat_id = call_or_message.chat.id
        message_id = None
        
    if not is_admin(user_id):
        if hasattr(call_or_message, 'data'):
            bot.answer_callback_query(call_or_message.id, "Немає доступу.")
        else:
            bot.send_message(chat_id, "Немає доступу.")
        return
    
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ ДОДАТИ ПОСВІДЧЕННЯ", callback_data="add_cert"))
    kb.add(types.InlineKeyboardButton("➖ ВИДАЛИТИ ПОСВІДЧЕННЯ", callback_data="del_cert"))
    kb.add(types.InlineKeyboardButton("✏️ РЕДАГУВАТИ ПОСВІДЧЕННЯ", callback_data="edit_cert"))
    kb.add(types.InlineKeyboardButton("⬅️ НАЗАД", callback_data="back_to_main"))
    
    try:
        if message_id:  # Это CallbackQuery
            bot.edit_message_text("🔧 Адмін-панель", chat_id, message_id, reply_markup=kb)
        else:  # Это Message
            bot.send_message(chat_id, "🔧 Адмін-панель", reply_markup=kb)
    except Exception as e:
        # Если редактирование не удалось, отправляем новое сообщение
        print(f"Помилка при відображенні адмін-панелі: {e}")
        bot.send_message(chat_id, "🔧 Адмін-панель", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "add_cert")
def add_cert_step1(call):
    bot.answer_callback_query(call.id)
    user_states[call.from_user.id] = "adding_cert"
    msg = bot.send_message(call.message.chat.id, "Введіть назву посвідчення:", reply_markup=cancel_kb)
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
        msg = bot.send_message(message.chat.id, "❌ Посвідчення з такою назвою вже існує. Введіть іншу назву:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, add_cert_desc)
        return
    
    bot.send_message(message.chat.id, f"Введіть опис для '{name}':", reply_markup=cancel_kb)
    bot.register_next_step_handler(message, lambda m: add_cert_price(m, name))

def add_cert_price(message, name):
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
        bot.register_next_step_handler(msg, lambda m: add_cert_price(m, name))
        return
    
    bot.send_message(message.chat.id, f"Введіть ціну для '{name}':", reply_markup=cancel_kb)
    bot.register_next_step_handler(message, lambda m: add_cert_photo(m, name, desc))

def add_cert_photo(message, name, desc):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Додавання скасовано.")
        show_admin_panel(message)
        return
    
    price = message.text.strip()
    if not price:
        msg = bot.send_message(message.chat.id, "❌ Ціна не може бути порожньою. Спробуйте ще раз:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, lambda m: add_cert_photo(m, name, desc))
        return
    
    data['certificate_details'][name] = {'description': desc, 'price': price}
    msg = bot.send_message(message.chat.id, "📷 Надішліть фото:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, lambda m: save_cert_photo(m, name))

def save_cert_photo(message, name):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Додавання скасовано.")
        show_admin_panel(message)
        return
    
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Будь ласка, надішліть фото.", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, lambda m: save_cert_photo(m, name))
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        path = os.path.join(PHOTO_DIR, f"{name}.jpg")
        with open(path, 'wb') as f:
            f.write(downloaded)
        
        data['certificate_details'][name]['photo'] = path
        data['certificates'].append(name)
        save_data()
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "✅ Посвідчення успішно додано!")
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
    kb.add(types.InlineKeyboardButton("❌ СКАСУВАТИ РЕДАГУВАННЯ", callback_data="cancel_edit_cert"))
    
    try:
        bot.edit_message_text("Оберіть посвідчення для редагування:", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні списку для редагування: {e}")
        bot.send_message(call.message.chat.id, "Оберіть посвідчення для редагування:", reply_markup=kb)

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
    kb.add(types.InlineKeyboardButton("💵 ЗМІНИТИ ЦІНУ", callback_data=f"edit_price_{name}"))
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
        msg = bot.send_message(message.chat.id, "❌ Посвідчення з такою назвою вже існує. Введіть іншу назву:", reply_markup=cancel_kb)
        bot.register_next_step_handler(msg, save_edited_name)
        return
    
    # Копируем данные со старого названия на новое
    cert_data = data['certificate_details'][old_name]
    data['certificate_details'][new_name] = cert_data
    del data['certificate_details'][old_name]
    
    # Обновляем список сертификатов
    data['certificates'] = [new_name if c == old_name else c for c in data['certificates']]
    
    # Обновляем имя фото, если оно есть
    old_photo_path = cert_data.get('photo')
    if old_photo_path and os.path.exists(old_photo_path):
        new_photo_path = os.path.join(PHOTO_DIR, f"{new_name}.jpg")
        os.rename(old_photo_path, new_photo_path)
        data['certificate_details'][new_name]['photo'] = new_photo_path
    
    save_data()
    clear_user_state(message.from_user.id)
    bot.send_message(message.chat.id, f"✅ Назву успішно змінено з '{old_name}' на '{new_name}'!")
    show_admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_desc_"))
def edit_cert_desc(call):
    name = call.data.replace("edit_desc_", "")
    user_states[call.from_user.id] = {'editing': name, 'field': 'description'}
    msg = bot.send_message(call.message.chat.id, f"Введіть новий опис для {name}:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, save_edited_field)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_price_"))
def edit_cert_price(call):
    name = call.data.replace("edit_price_", "")
    user_states[call.from_user.id] = {'editing': name, 'field': 'price'}
    msg = bot.send_message(call.message.chat.id, f"Введіть нову ціну для {name}:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, save_edited_field)

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_photo_"))
def edit_cert_photo(call):
    name = call.data.replace("edit_photo_", "")
    user_states[call.from_user.id] = {'editing': name, 'field': 'photo'}
    msg = bot.send_message(call.message.chat.id, f"Надішліть нове фото для {name}:", reply_markup=cancel_kb)
    bot.register_next_step_handler(msg, save_edited_field)

def save_edited_field(message):
    if message.from_user.id not in user_states:
        return
    if message.text and message.text.strip() == "❌ СКАСУВАТИ":
        clear_user_state(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Редагування скасовано.")
        show_admin_panel(message)
        return
    
    user_data = user_states[message.from_user.id]
    name = user_data['editing']
    field = user_data['field']
    
    if field == 'description':
        new_value = message.text.strip()
        if not new_value:
            msg = bot.send_message(message.chat.id, "❌ Опис не може бути порожнім. Спробуйте ще раз:", reply_markup=cancel_kb)
            bot.register_next_step_handler(msg, save_edited_field)
            return
        data['certificate_details'][name]['description'] = new_value
    elif field == 'price':
        new_value = message.text.strip()
        if not new_value:
            msg = bot.send_message(message.chat.id, "❌ Ціна не може бути порожньою. Спробуйте ще раз:", reply_markup=cancel_kb)
            bot.register_next_step_handler(msg, save_edited_field)
            return
        data['certificate_details'][name]['price'] = new_value
    elif field == 'photo':
        if not message.photo:
            msg = bot.send_message(message.chat.id, "❌ Будь ласка, надішліть фото.", reply_markup=cancel_kb)
            bot.register_next_step_handler(msg, save_edited_field)
            return
        try:
            old_photo = data['certificate_details'][name].get('photo')
            if old_photo and os.path.exists(old_photo):
                os.remove(old_photo)
            
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded = bot.download_file(file_info.file_path)
            path = os.path.join(PHOTO_DIR, f"{name}.jpg")
            with open(path, 'wb') as f:
                f.write(downloaded)
            new_value = path
            data['certificate_details'][name]['photo'] = new_value
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Помилка при збереженні фото: {str(e)}")
            show_admin_panel(message)
            return
    
    save_data()
    clear_user_state(message.from_user.id)
    bot.send_message(message.chat.id, f"✅ {name} успішно оновлено!")
    show_admin_panel(message)

@bot.callback_query_handler(func=lambda call: call.data == "del_cert")
def del_cert(call):
    if is_spamming(call.from_user.id):
        return
    kb = types.InlineKeyboardMarkup()
    for cert in data['certificates']:
        kb.add(types.InlineKeyboardButton(cert, callback_data=f"del_{cert}"))
    kb.add(types.InlineKeyboardButton("❌ СКАСУВАТИ ВИДАЛЕННЯ", callback_data="cancel_del_cert"))
    
    try:
        bot.edit_message_text("Оберіть посвідчення для видалення:", call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception as e:
        print(f"Помилка при відображенні списку для видалення: {e}")
        bot.send_message(call.message.chat.id, "Оберіть посвідчення для видалення:", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_del_cert")
def cancel_delete_cert(call):
    bot.answer_callback_query(call.id, "❌ Видалення скасовано.")
    show_admin_panel(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def confirm_delete(call):
    name = call.data.replace("del_", "")
    data['certificates'] = [c for c in data['certificates'] if c != name]
    if name in data['certificate_details']:
        path = data['certificate_details'][name].get('photo')
        if path and os.path.exists(path):
            os.remove(path)
        del data['certificate_details'][name]
    save_data()
    bot.answer_callback_query(call.id, "✅ Видалено.")
    show_admin_panel(call)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    show_main_menu(call)

print("🤖 Бот запущений!")

# Эта строка добавляет режим бесконечного опроса сервера Telegram
# и удерживает бота работающим
bot.polling(none_stop=True, interval=0)