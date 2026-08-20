import os
import sqlite3
from flask import Flask
from threading import Thread
import telebot
from telebot import types

TOKEN = "8816940858:AAEwDQ94ues00rcG1RVkNMPumQh7Xxgfowc"
ADMIN_ID = 8753350906

bot = telebot.TeleBot(TOKEN)
user_states = {}

# --- SQLITE BAZA ---
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'uz',
            is_vip INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            video_id TEXT,
            is_vip INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('bot_database.db', check_same_thread=False)

# --- FLASK SERVER (RENDER 24/7) ---
app = Flask('')
@app.route('/')
def home():
    return "Kino Bot 24/7 ishlayapti!"

def run():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run).start()

# --- TEKSHIRUVLAR ---
def check_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False
    return True

def get_user_lang(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'uz'

def is_user_vip(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_vip FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

TEXTS = {
    'uz': {
        'menu': "✅ Asosiy menyu:",
        'sub_text': "✨ Botdan foydalanish uchun quyidagi barcha kanal va guruhlarga obuna bo'ling:",
        'check': "🔄 Tekshirish",
        'vip_menu': "💎 Premium Obuna",
        'search': "🔍 Qidirish",
        'random': "🎲 Tasodifiy",
        'recommend': "💡 Kino tavsiya qilish",
        'personal_add': "📬 Shaxsiy kino qo'shish",
        'admin_add': "🎬 Admin orqali kino qo'shish",
        'lang_change': "🌐 Tilni o'zgartirish",
        'reklama': "📢 Reklama"
    }
}

def get_text(user_id, key):
    lang = get_user_lang(user_id)
    return TEXTS.get(lang, TEXTS['uz']).get(key, key)

def show_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(get_text(user_id, 'search'), get_text(user_id, 'random'))
    markup.row(get_text(user_id, 'recommend'), get_text(user_id, 'personal_add'))
    markup.row(get_text(user_id, 'admin_add'), get_text(user_id, 'vip_menu'))
    markup.row(get_text(user_id, 'reklama'), get_text(user_id, 'lang_change'))
    
    if user_id == ADMIN_ID:
        markup.row("📢 Kanallarni sozlash", "📊 Statistika")
        markup.row("🎬 Kino yuklash", "🤖 Bot holati")
        
    bot.send_message(chat_id, get_text(user_id, 'menu'), reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "❌ Siz botdan bloklangansiz!")
        return

    if not is_user_vip(user_id) and not check_sub(user_id):
        lang = get_user_lang(user_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kino olami", url="https://t.me/max_films01"))
        markup.add(types.InlineKeyboardButton("📢 Reklama Xizmati", url="https://t.me/reklamuchun1"))
        markup.add(types.InlineKeyboardButton("👥 Sevishganlar guruhi", url="https://t.me/sevshgnrlr"))
        markup.add(types.InlineKeyboardButton(TEXTS[lang]['check'], callback_data="check_subscription"))
        markup.add(types.InlineKeyboardButton(TEXTS[lang]['vip_menu'], callback_data="btn_vip_menu"))
        
        bot.send_message(message.chat.id, TEXTS[lang]['sub_text'], reply_markup=markup)
        return

    show_main_menu(message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_sub(call):
    user_id = call.from_user.id
    if check_sub(user_id):
        bot.answer_callback_query(call.id, "Rahmat! Obuna tasdiqlandi ✅")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        show_main_menu(call.message.chat.id, user_id)
    else:
        bot.answer_callback_query(call.id, "Siz hali hamma kanal va guruhlarga a'zo bo'lmadingiz! ❌", show_alert=True)

# --- ADMIN PANEL & QOLGAN FUNKSIYALAR ---
@bot.message_handler(func=lambda message: message.text == "📊 Statistika" and message.from_user.id == ADMIN_ID)
def admin_stats_panel(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM movies')
    total_movies = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = 1')
    total_vips = cursor.fetchone()[0]
    conn.close()
    bot.reply_to(message, f"📊 **Bot Statistikasi:**\n\n👥 Jami foydalanuvchilar: {total_users}\n💎 VIP foydalanuvchilar: {total_vips}\n🎬 Jami kinolar: {total_movies}", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🤖 Bot holati" and message.from_user.id == ADMIN_ID)
def admin_bot_status(message):
    bot.reply_to(message, "🟢 Bot holati: **Aktiv (24/7 ishlayapti)**\n⚡ Server: Render\n🗄 Ma'lumotlar bazasi: SQLite (Ulandi)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 Kanallarni sozlash" and message.from_user.id == ADMIN_ID)
def admin_channels_config(message):
    bot.reply_to(message, "📢 **Majburiy obuna kanal va guruhlari muvaffaqiyatli sozlandi.**", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🎬 Kino yuklash" and message.from_user.id == ADMIN_ID)
def admin_movie_upload_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 Oddiy video qo'shish", callback_data="add_type_0"))
    markup.add(types.InlineKeyboardButton("💎 VIP video qo'shish", callback_data="add_type_1"))
    bot.send_message(message.chat.id, "🔽 Quyidagilardan birini tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_type_"))
def callback_add_type(call):
    if call.from_user.id != ADMIN_ID:
        return
    v_type = int(call.data.split("_")[2])
    user_states[call.from_user.id] = {"step": "admin_direct_wait_video", "type": v_type}
    v_name = "VIP" if v_type == 1 else "Oddiy"
    bot.edit_message_text(f"📤 {v_name} videoni yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['ban'])
def ban_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Foydalanish: `/ban [user_id]`", parse_mode="Markdown")
        return
    target_id = int(parts[1])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (target_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ `{target_id}` ban qilindi.", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Foydalanish: `/unban [user_id]`", parse_mode="Markdown")
        return
    target_id = int(parts[1])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (target_id,))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ `{target_id}` bandan olindi.", parse_mode="Markdown")

@bot.message_handler(commands=['vip'])
def vip_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Foydalanish: `/vip [user_id]`", parse_mode="Markdown")
        return
    target_id = int(parts[1])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_vip = 1 WHERE user_id = ?', (target_id,))
    conn.commit()
    conn.close()
    bot.send_message(target_id, "🎉 Tabriklaymiz! Sizga VIP obuna berildi! ✅")
    bot.reply_to(message, f"✅ `{target_id}` ga VIP berildi.", parse_mode="Markdown")

@bot.message_handler(commands=['unvip'])
def unvip_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Foydalanish: `/unvip [user_id]`", parse_mode="Markdown")
        return
    target_id = int(parts[1])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_vip = 0 WHERE user_id = ?', (target_id,))
    conn.commit()
    conn.close()
    bot.send_message(target_id, "❌ Sizning VIP obunangiz admin tomonidan olib tashlandi.")
    bot.reply_to(message, f"✅ `{target_id}` dan VIP olib tashlandi.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in [TEXTS['uz']['vip_menu']])
def vip_subscription_menu_msg(message):
    vip_subscription_menu(message)

@bot.callback_query_handler(func=lambda call: call.data == "btn_vip_menu")
def vip_subscription_menu_call(call):
    vip_subscription_menu(call)

def vip_subscription_menu(event):
    chat_id = event.message.chat.id if hasattr(event, 'message') else event.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("1 oylik — 15,000 so'm", callback_data="pay_uz_1"))
    markup.add(types.InlineKeyboardButton("3 oylik — 20,000 so'm", callback_data="pay_uz_3"))
    markup.add(types.InlineKeyboardButton("6 oylik — 35,000 so'm", callback_data="pay_uz_6"))
    text = "💎 **Premium Obuna**\nTarifni tanlang:"
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def vip_payment_details(call):
    data_parts = call.data.split("_")
    period = data_parts[2]
    prices = {"1": "15,000 so'm", "3": "20,000 so'm", "6": "35,000 so'm"}
    price = prices.get(period, "15,000 so'm")
    text = (
        f"💎 **Tarif:** {period} oylik ({price})\n\n"
        f"💳 **Karta raqam:** `6262 5701 4806 4381`\n"
        f"👤 **Karta egasi:** Obidjonova M\n\n"
        f"📸 Pulni o'tkazgach, to'lov chekining **skrinshotini** shu botga yuboring. Admin tasdiqlagach VIP obuna avtomatik ochiladi!"
    )
    user_states[call.from_user.id] = f"waiting_for_check_{period}"
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == TEXTS['uz']['recommend'])
def recommend_movie(message):
    user_states[message.from_user.id] = "recommending_movie"
    bot.send_message(message.chat.id, "✍️ Ko'rmoqchi bo'lgan kinosingiz nomini yozib yuboring, adminga yuboramiz:")

@bot.message_handler(func=lambda message: message.text == TEXTS['uz']['personal_add'])
def personal_add_movie(message):
    user_states[message.from_user.id] = "personal_add_video"
    bot.send_message(message.chat.id, "📤 Shaxsiy kino videosini yuboring:")

@bot.message_handler(func=lambda message: message.text == TEXTS['uz']['admin_add'])
def admin_add_movie(message):
    user_states[message.from_user.id] = "admin_add_video"
    bot.send_message(message.chat.id, "📤 Adminga yuborish uchun kino videosini yuboring:")

@bot.message_handler(func=lambda message: message.text == TEXTS['uz']['random'])
def random_movie(message):
    conn = get_db()
    cursor = conn.cursor()
    if is_user_vip(message.from_user.id):
        cursor.execute('SELECT code, video_id, is_vip FROM movies')
    else:
        cursor.execute('SELECT code, video_id, is_vip FROM movies WHERE is_vip = 0')
    movies = cursor.fetchall()
    conn.close()

    if not movies:
        bot.send_message(message.chat.id, "❌ Hozircha bazada mos kinolar yo'q.")
    else:
        import random
        code, video_id, is_vip = random.choice(movies)
        bot.send_video(message.chat.id, video_id, caption=f"🎲 Tasodifiy kino (Kodi: `{code}`)", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == TEXTS['uz']['search'])
def search_hint(message):
    bot.send_message(message.chat.id, "🔎 Kino topish uchun kino **kodini** yuboring (masalan: `1`, `120` yoki `122`):", parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'video', 'photo'])
def handle_all_inputs(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

    state = user_states.get(user_id)
    text = message.text or message.caption or ""

    if user_id == ADMIN_ID:
        if message.video and isinstance(state, dict) and state.get("step") == "admin_direct_wait_video":
            user_states[user_id]["video"] = message.video.file_id
            user_states[user_id]["step"] = "admin_direct_wait_code"
            bot.reply_to(message, "🔢 Video qabul qilindi. Endi kino kodini yuboring:")
            return

        if isinstance(state, dict) and state.get("step") == "admin_direct_wait_code":
            v_type = state["type"]
            code = text.strip()
            video_id = state["video"]
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO movies (code, video_id, is_vip) VALUES (?, ?, ?)', (code, video_id, v_type))
            conn.commit()
            conn.close()
            
            user_states.pop(user_id, None)
            v_name = "VIP" if v_type == 1 else "ODDIY"
            bot.reply_to(message, f"✅ Muvaffaqiyatli! `{code}` kodli **{v_name}** kino bazaga saqlandi.", parse_mode="Markdown")
            return

    if state and state.startswith("waiting_for_check_"):
        if message.photo:
            period = state.split("_")[-1]
            user_states.pop(user_id, None)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"vip_yes_{user_id}_{period}"),
                types.InlineKeyboardButton("❌ Rad etish", callback_data=f"vip_no_{user_id}")
            )
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(ADMIN_ID, f"👤 Foydalanuvchi: @{message.from_user.username} ({user_id})\n💎 Tarif: {period} oylik VIP obuna so'rayapti.", reply_markup=markup)
            bot.reply_to(message, "✅ Chekingiz adminga yuborildi! Tez orada tekshirib ulab berishadi.")
            return
        else:
            bot.reply_to(message, "❌ Iltimos, to'lov chekining rasmini (skrinshot) yuboring!")
            return

    if state == "recommending_movie":
        user_states.pop(user_id, None)
        bot.send_message(ADMIN_ID, f"💡 **Yangi kino tavsiyasi:**\nKimdan: @{message.from_user.username} ({user_id})\nKino: {text}")
        bot.reply_to(message, "✅ Tavsiyangiz adminga yuborildi!")
        return

    if state == "personal_add_video" and message.video:
        user_states[user_id] = {"video": message.video.file_id, "step": "personal_get_code"}
        bot.reply_to(message, "🔢 Bu kino uchun kod yuboring:")
        return

    if isinstance(state, dict) and state.get("step") == "personal_get_code":
        code = text.strip()
        video_id = state.get("video")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO movies (code, video_id, is_vip) VALUES (?, ?, 0)', (code, video_id))
        conn.commit()
        conn.close()
        
        user_states.pop(user_id, None)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Reklama berish", url="https://t.me/reklamuchun1"))
        markup.add(types.InlineKeyboardButton("💎 Premium Obuna", callback_data="btn_vip_menu"))
        
        bot.send_message(message.chat.id, f"✅ Kino muvaffaqiyatli bazaga qo'shildi! Kodi: `{code}`", reply_markup=markup, parse_mode="Markdown")
        return

    code = text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT video_id, is_vip FROM movies WHERE code = ?', (code,))
    movie = cursor.fetchone()
    conn.close()

    if movie:
        video_id, is_vip = movie
        if is_vip == 1 and not is_user_vip(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💎 Premium Obuna sotib olish", callback_data="btn_vip_menu"))
            bot.send_message(message.chat.id, "💎 Bu kino faqat **VIP foydalanuvchilar** uchun mo'ljallangan! Ko'rish uchun VIP obuna sotib oling:", reply_markup=markup, parse_mode="Markdown")
            return
        
        v_label = "💎 VIP kino" if is_vip == 1 else "🎬 Kino"
        bot.send_video(message.chat.id, video_id, caption=f"{v_label}! Kodi: `{code}`", parse_mode="Markdown")
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Reklama", url="https://t.me/reklamuchun1"))
        markup.add(types.InlineKeyboardButton("💎 Premium Obuna", callback_data="btn_vip_menu"))
        bot.reply_to(message, f"❌ `{code}` kodi bo'yicha hech qanday kino topilmadi.", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("vip_"))
def admin_vip_control(call):
    data = call.data.split("_")
    action = data[1]
    
    id_val = int(data[2])
    if action == "yes":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_vip = 1 WHERE user_id = ?', (id_val,))
        conn.commit()
        conn.close()
        bot.send_message(id_val, "🎉 Tabriklaymiz! Sizning VIP obunangiz admin tomonidan tasdiqlandi va faollashtirildi! ✅")
        bot.answer_callback_query(call.id, "VIP tasdiqlandi! ✅")
    else:
        bot.send_message(id_val, "❌ To'lov chekingiz rad etildi.")
        bot.answer_callback_query(call.id, "Rad etildi ❌")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

if __name__ == "__main__":
    bot.infinity_polling()
