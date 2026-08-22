import sqlite3
import telebot
from telebot import types
import random
from datetime import datetime, timedelta

TOKEN = "8816940858:AAEwDQ94ues00rcG1RVkNMPumQh7Xxgfowc"
ADMIN_ID = 8753350906
BOT_USERNAME = "Kinolarqbot"
MY_USERNAME = "@reklamuchun1"  # Zakaz yoki reklama uchun sizning lichkangiz

bot = telebot.TeleBot(TOKEN)
user_states = {}

# --- BAZA YO'LI ---
DB_NAME = 'bot_database.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_date TEXT,
            is_vip INTEGER DEFAULT 0,
            vip_expire_date TEXT,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            video_id TEXT,
            is_vip INTEGER DEFAULT 0,
            downloads INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            channel_username TEXT PRIMARY KEY
        )
    ''')
    conn.commit()
    
    cursor.execute('SELECT COUNT(*) FROM channels')
    if cursor.fetchone()[0] == 0:
        default_channels = ["@max_films01", "@reklamuchun1", "@sevshgnrlr"]
        for ch in default_channels:
            cursor.execute('INSERT OR IGNORE INTO channels (channel_username) VALUES (?)', (ch,))
        conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def get_current_channels():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT channel_username FROM channels')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def check_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    current_channels = get_current_channels()
    for ch in current_channels:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Obunani tekshirishda xatolik ({ch}): {e}")
            return False
    return True

def is_user_vip(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_vip, vip_expire_date FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False
    
    is_vip, expire_date_str = row
    if is_vip == 1:
        if expire_date_str:
            expire_date = datetime.strptime(expire_date_str, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > expire_date:
                remove_vip_status(user_id)
                return False
        return True
    return False

def remove_vip_status(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_vip = 0, vip_expire_date = NULL WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_user_banned(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def show_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Qidirish", "🎲 Tasodifiy")
    markup.row("💡 Kino tavsiya qilish", "📬 Shaxsiy kino qo'shish")
    markup.row("🎬 Admin orqali kino qo'shish", "💎 Premium Obuna")
    markup.row("📢 Reklama")
    
    if user_id == ADMIN_ID:
        markup.row("📊 Statistika", "📢 Xabar yuborish (Reklama)")
        markup.row("🎬 Kino yuklash", "🤖 Bot holati")
        markup.row("📢 Kanallarni sozlash", "➕ Kanal qo'shish")
        markup.row("🗑 Kanalni o'chirish", "🚫 VIP'dan chiqarish")
        
    bot.send_message(chat_id, "✅ Asosiy menyu:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)', (user_id, username, current_date))
    conn.commit()
    conn.close()

    if is_user_banned(user_id):
        bot.send_message(message.chat.id, "❌ Siz botdan bloklangansiz!")
        return

    if not is_user_vip(user_id) and not check_sub(user_id):
        markup = types.InlineKeyboardMarkup()
        current_channels = get_current_channels()
        for ch in current_channels:
            ch_clean = ch.replace("@", "").replace("https://t.me/", "")
            markup.add(types.InlineKeyboardButton(f"📢 Kanalga o'tish", url=f"https://t.me/{ch_clean}"))
            
        markup.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="check_subscription"))
        markup.add(types.InlineKeyboardButton("💎 Premium Obuna", callback_data="btn_vip_menu"))
        
        bot.send_message(message.chat.id, "✨ Botdan foydalanish uchun quyidagi barcha kanallarga obuna bo'ling:", reply_markup=markup)
        return

    text = message.text or ""
    if text.startswith("/start kino_"):
        code = text.split("_")[1]
        send_movie_by_code(message.chat.id, user_id, code)
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
        bot.answer_callback_query(call.id, "Siz hali hamma kanallarga a'zo bo'lmadingiz! ❌", show_alert=True)

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
    cursor.execute('SELECT SUM(downloads) FROM movies')
    total_downloads = cursor.fetchone()[0] or 0
    conn.close()
    
    stats_text = (
        f"📊 **Botning To'liq Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total_users}</b> ta\n"
        f"💎 VIP obunachilar: <b>{total_vips}</b> ta\n"
        f"🎬 Bazadagi jami kinolar: <b>{total_movies}</b> ta\n"
        f"📥 Jami ko'rilgan/yuklangan kinolar: <b>{total_downloads}</b> marta\n"
        f"🟢 Bot holati: <b>Ishlayapti (24/7)</b>"
    )
    bot.reply_to(message, stats_text, parse_mode="HTML")

@bot.message_handler(func=lambda message: message.text == "🤖 Bot holati" and message.from_user.id == ADMIN_ID)
def admin_bot_status(message):
    bot.reply_to(message, "🟢 Bot holati: **Aktiv (24/7 ishlayapti)**\n⚡ Himoya: Yoqilgan (`protect_content` faol)\n🗄 Ma'lumotlar bazasi: SQLite", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 Kanallarni sozlash" and message.from_user.id == ADMIN_ID)
def admin_channels_config(message):
    current_channels = get_current_channels()
    channels_str = "\n".join(current_channels) if current_channels else "Hozircha kanallar yo'q."
    bot.reply_to(message, f"📢 **Hozirgi majburiy obuna kanallari:**\n{channels_str}\n\n⚠️ *Eslatma: Bot barcha kanallarga administrator bo'lishi shart!*", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "➕ Kanal qo'shish" and message.from_user.id == ADMIN_ID)
def admin_add_channel_start(message):
    user_states[message.from_user.id] = "waiting_for_new_channel"
    bot.reply_to(message, "➕ Yangi kanal username'i yoki havolasini yuboring (Masalan: `@kanal_nomi` yoki `https://t.me/kanal_nomi`):")

@bot.message_handler(func=lambda message: message.text == "🗑 Kanalni o'chirish" and message.from_user.id == ADMIN_ID)
def admin_remove_channel_start(message):
    current_channels = get_current_channels()
    if not current_channels:
        bot.reply_to(message, "❌ Hozircha majburiy obunada kanallar mavjud emas.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for ch in current_channels:
        markup.add(types.InlineKeyboardButton(f"❌ O'chirish: {ch}", callback_data=f"del_ch_{ch}"))
        
    bot.reply_to(message, "🗑 Majburiy obunadan chiqarmoqchi (o'chirmoqchi) bo'lgan kanalingizni pastdagi tugmalardan tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_ch_"))
def callback_delete_channel(call):
    if call.from_user.id != ADMIN_ID:
        return
    channel_name = call.data.replace("del_ch_", "")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM channels WHERE channel_username = ?', (channel_name,))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, f"{channel_name} o'chirildi!")
    try:
        bot.edit_message_text(f"✅ <b>{channel_name}</b> majburiy obuna ro'yxatidan muvaffaqiyatli olib tashlandi!", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except:
        pass

@bot.message_handler(func=lambda message: message.text == "🚫 VIP'dan chiqarish" and message.from_user.id == ADMIN_ID)
def admin_remove_vip_start(message):
    user_states[message.from_user.id] = "waiting_for_remove_vip_id"
    bot.reply_to(message, "👤 VIP statusini olib tashlamoqchi bo'lgan foydalanuvchining **Telegram ID** raqamini yuboring:")

@bot.message_handler(func=lambda message: message.text == "📢 Xabar yuborish (Reklama)" and message.from_user.id == ADMIN_ID)
def admin_start_broadcast(message):
    user_states[message.from_user.id] = "waiting_for_broadcast_text"
    bot.reply_to(message, "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni (matn, rasm yoki video) yuboring:")

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

@bot.message_handler(func=lambda message: message.text == "💎 Premium Obuna")
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

@bot.message_handler(func=lambda message: message.text == "💡 Kino tavsiya qilish")
def recommend_movie(message):
    user_states[message.from_user.id] = "recommending_movie"
    bot.send_message(message.chat.id, "✍️ Ko'rmoqchi bo'lgan kinosingiz nomini yozib yuboring, adminga yuboramiz:")

@bot.message_handler(func=lambda message: message.text == "📬 Shaxsiy kino qo'shish")
def personal_add_movie(message):
    user_states[message.from_user.id] = "personal_add_video"
    bot.send_message(message.chat.id, "📤 Shaxsiy kino videosini yuboring:")

@bot.message_handler(func=lambda message: message.text == "🎬 Admin orqali kino qo'shish")
def admin_add_movie(message):
    user_states[message.from_user.id] = "admin_add_video"
    bot.send_message(message.chat.id, "📤 Adminga yuborish uchun kino videosini yuboring:")

@bot.message_handler(func=lambda message: message.text == "🎲 Tasodifiy")
def random_movie(message):
    conn = get_db()
    cursor = conn.cursor()
    if is_user_vip(message.from_user.id):
        cursor.execute('SELECT code, video_id, is_vip, downloads FROM movies')
    else:
        cursor.execute('SELECT code, video_id, is_vip, downloads FROM movies WHERE is_vip = 0')
    movies = cursor.fetchall()
    conn.close()

    if not movies:
        bot.send_message(message.chat.id, "❌ Hozircha bazada kinolar mavjud emas.")
    else:
        code, video_id, is_vip, downloads = random.choice(movies)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE movies SET downloads = downloads + 1 WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        new_downloads = downloads + 1

        caption = (
            f"🎬 **Kino kodi:** `{code}`\n\n"
            f"🔥 **ZAYAFKA KANALLARGA ZAKAZ OLAMAN!**\n\n"
            f"Kanalga odam kerakmi? Unda yozing 👇\n"
            f"👥 Jivoy, aktiv auditoriya\n"
            f"⚡ Tez va sifatli ishlaymiz\n"
            f"💸 Narxlar hamyonbop\n"
            f"📈 Kanalni tezroq o'stirishga yordam beramiz\n\n"
            f"1000 ta zayafka — kelishilgan narxda ✅\n"
            f"Ko'p miqdorga alohida skidka bor 💥\n\n"
            f"📬 Zakaz uchun lichkaga yozing\n"
            f"{MY_USERNAME}\n\n"
            f"⬇️ Yuklab olingan: {new_downloads} ta"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📢 Reklama / Zakaz", url=f"https://t.me/{MY_USERNAME.replace('@', '')}"),
            types.InlineKeyboardButton("💎 Premium obuna", callback_data="btn_vip_menu")
        )
        
        bot.send_video(message.chat.id, video_id, caption=caption, parse_mode="Markdown", reply_markup=markup, protect_content=True)

@bot.message_handler(func=lambda message: message.text == "🔍 Qidirish")
def search_hint(message):
    bot.send_message(message.chat.id, "🔎 Kino topish uchun kino **kodini** yuboring (masalan: `1`, `120`):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 Reklama")
def reklama_menu(message):
    bot.send_message(message.chat.id, f"📢 Reklama va xizmatlardan foydalanish uchun murojaat qiling: {MY_USERNAME}")

def send_movie_by_code(chat_id, user_id, code):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT video_id, is_vip, downloads FROM movies WHERE code = ?', (code,))
    movie = cursor.fetchone()
    conn.close()

    if movie:
        video_id, is_vip, downloads = movie
        if is_vip == 1 and not is_user_vip(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💎 Premium Obuna sotib olish", callback_data="btn_vip_menu"))
            bot.send_message(chat_id, "💎 Bu kino faqat **VIP foydalanuvchilar** uchun mo'ljallangan!", reply_markup=markup, parse_mode="Markdown")
            return
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE movies SET downloads = downloads + 1 WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        new_downloads = downloads + 1

        caption = (
            f"🎬 **Kino kodi:** `{code}`\n\n"
            f"🔥 **ZAYAFKA KANALLARGA ZAKAZ OLAMAN!**\n\n"
            f"Kanalga odam kerakmi? Unda yozing 👇\n"
            f"👥 Jivoy, aktiv auditoriya\n"
            f"⚡ Tez va sifatli ishlaymiz\n"
            f"💸 Narxlar hamyonbop\n"
            f"📈 Kanalni tezroq o'stirishga yordam beramiz\n\n"
            f"1000 ta zayafka — kelishilgan narxda ✅\n"
            f"Ko'p miqdorga alohida skidka bor 💥\n\n"
            f"📬 Zakaz uchun lichkaga yozing\n"
            f"{MY_USERNAME}\n\n"
            f"⬇️ Yuklab olingan: {new_downloads} ta"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📢 Reklama / Zakaz", url=f"https://t.me/{MY_USERNAME.replace('@', '')}"),
            types.InlineKeyboardButton("💎 Premium obuna", callback_data="btn_vip_menu")
        )
        
        bot.send_video(chat_id, video_id, caption=caption, parse_mode="Markdown", reply_markup=markup, protect_content=True)
    else:
        bot.send_message(chat_id, f"❌ `{code}` kodi bo'yicha hech qanday kino topilmadi.", parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'video', 'photo', 'document', 'audio'])
def handle_all_inputs(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

    state = user_states.get(user_id)
    text = message.text or message.caption or ""

    if user_id == ADMIN_ID:
        if state == "waiting_for_remove_vip_id":
            target_id = text.strip()
            user_states.pop(user_id, None)
            try:
                target_id = int(target_id)
                remove_vip_status(target_id)
                bot.reply_to(message, f"✅ ID: {target_id} bo'lgan foydalanuvchidan VIP statusi olib tashlandi!")
                bot.send_message(target_id, "⚠️ Sizning VIP obunangiz admin tomonidan yakunlandi.")
            except Exception as e:
                bot.reply_to(message, f"❌ Xatolik yuz berdi: {e}")
            return

        if state == "waiting_for_new_channel":
            channel_input = text.strip()
            if "t.me/" in channel_input:
                channel_input = "@" + channel_input.split("t.me/")[-1].strip("/")
            elif not channel_input.startswith("@"):
                channel_input = "@" + channel_input
            
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO channels (channel_username) VALUES (?)', (channel_input,))
            conn.commit()
            conn.close()
            
            user_states.pop(user_id, None)
            bot.reply_to(message, f"✅ {channel_input} majburiy obuna kanallari ro'yxatiga muvaffaqiyatli qo'shildi!")
            return

        if state == "waiting_for_broadcast_text":
            user_states.pop(user_id, None)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM u
