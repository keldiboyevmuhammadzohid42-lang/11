import sqlite3
import telebot
from telebot import types
import random
from datetime import datetime

TOKEN = "8816940858:AAEwDQ94ues00rcG1RVkNMPumQh7Xxgfowc"
ADMIN_ID = 8753350906

# Majburiy obuna kanallari
CHANNELS = [
    "@max_films01",     
    "@reklamuchun1",    
    "@sevshgnrlr"       
]

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
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def check_sub(user_id):
    if user_id == ADMIN_ID:
        return True
    for ch in CHANNELS:
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

def show_main_menu(chat_id, user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🔍 Qidirish", "🎲 Tasodifiy")
    markup.row("💡 Kino tavsiya qilish", "📬 Shaxsiy kino qo'shish")
    markup.row("🎬 Admin orqali kino qo'shish", "💎 Premium Obuna")
    markup.row("📢 Reklama")
    
    if user_id == ADMIN_ID:
        markup.row("📊 Statistika", "📢 Xabar yuborish (Reklama)")
        markup.row("🎬 Kino yuklash", "🤖 Bot holati")
        markup.row("📢 Kanallarni sozlash")
        
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
        markup.add(types.InlineKeyboardButton("📢 Kino olami", url="https://t.me/max_films01"))
        markup.add(types.InlineKeyboardButton("📢 Reklama Xizmati", url="https://t.me/reklamuchun1"))
        markup.add(types.InlineKeyboardButton("👥 Sevishganlar guruhi", url="https://t.me/sevshgnrlr"))
        markup.add(types.InlineKeyboardButton("🔄 Tekshirish", callback_data="check_subscription"))
        markup.add(types.InlineKeyboardButton("💎 Premium Obuna", callback_data="btn_vip_menu"))
        
        bot.send_message(message.chat.id, "✨ Botdan foydalanish uchun quyidagi barcha kanal va guruhlarga obuna bo'ling:", reply_markup=markup)
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
        f"📊 **Bot Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: {total_users} ta\n"
        f"💎 VIP obunachilar: {total_vips} ta\n"
        f"🎬 Bazadagi jami kinolar: {total_movies} ta\n"
        f"📥 Jami yuklab olishlar: {total_downloads} marta\n"
        f"🟢 Bot holati: Barqaror ishlayapti"
    )
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🤖 Bot holati" and message.from_user.id == ADMIN_ID)
def admin_bot_status(message):
    bot.reply_to(message, "🟢 Bot holati: **Aktiv (24/7 ishlayapti)**\n⚡ Himoya: Yoqilgan (`protect_content` faol)\n🗄 Ma'lumotlar bazasi: SQLite", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 Kanallarni sozlash" and message.from_user.id == ADMIN_ID)
def admin_channels_config(message):
    channels_str = "\n".join(CHANNELS)
    bot.reply_to(message, f"📢 **Majburiy obuna kanallari:**\n{channels_str}\n\n⚠️ *Eslatma: Bot barcha kanallarga administrator bo'lishi shart!*", parse_mode="Markdown")

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
            f"🔥 ZAYAFKA KANALLARGA ZAKAZ OLAMAN!\n\n"
            f"Kanalga odam kerakmi? Unda yoz 👇\n"
            f"👥 Jivoy, aktiv auditoriya\n"
            f"⚡ Tez va sifatli ishlaymiz\n"
            f"💸 Narxlar hamyonbop\n"
            f"📈 Kanalni tezroq o'stirishga yordam beramiz\n\n"
            f"1000 ta zayafka — kelishilgan narxda ✅\n"
            f"Ko'p miqdorga alohida skidka bor 💥\n\n"
            f"📩 Zakaz uchun lichkaga yozing\n"
            f"@mhdnvwv\n\n"
            f"⬇️ Yuklab olingan: {new_downloads} ta"
        )
        bot.send_video(message.chat.id, video_id, caption=caption, parse_mode="Markdown", protect_content=True)

@bot.message_handler(func=lambda message: message.text == "🔍 Qidirish")
def search_hint(message):
    bot.send_message(message.chat.id, "🔎 Kino topish uchun kino **kodini** yuboring (masalan: `1`, `120`):", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📢 Reklama")
def reklama_menu(message):
    bot.send_message(message.chat.id, "📢 Reklama xizmatidan foydalanish uchun murojaat qiling: @reklamuchun1")

@bot.message_handler(content_types=['text', 'video', 'photo', 'document', 'audio'])
def handle_all_inputs(message):
    user_id = message.from_user.id
    if is_user_banned(user_id):
        return

    state = user_states.get(user_id)
    text = message.text or message.caption or ""

    if user_id == ADMIN_ID:
        if state == "waiting_for_broadcast_text":
            user_states.pop(user_id, None)
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users')
            users = cursor.fetchall()
            conn.close()
            
            success = 0
            failed = 0
            bot.reply_to(message, "📢 Xabar tarqatish boshlandi...")
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for u in users:
                try:
                    bot.copy_message(u[0], message.chat.id, message.message_id)
                    success += 1
                except:
                    failed += 1
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            bot.send_message(ADMIN_ID, f"✅ Xabar yuborish tugadi.\n\n👤 Jami foydalanuvchilar: {len(users)}\n✅ Muvaffaqiyatli: {success}\n❌ Xato (bloklaganlar): {failed}\n⏱ Boshlanish vaqti: {start_time}\n⏱ Tugash vaqti: {end_time}")
            return

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
            cursor.execute('INSERT OR REPLACE INTO movies (code, video_id, is_vip, downloads) VALUES (?, ?, ?, 0)', (code, video_id, v_type))
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
        bot.send_message(ADMIN_ID, f"💡 **Kino tavsiyasi:**\nKimdan: @{message.from_user.username} ({user_id})\nKino: {text}")
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
        cursor.execute('INSERT OR REPLACE INTO movies (code, video_id, is_vip, downloads) VALUES (?, ?, 0, 0)', (code, video_id))
        conn.commit()
        conn.close()
        
        user_states.pop(user_id, None)
        bot.send_message(message.chat.id, f"✅ Kino bazaga qo'shildi! Kodi: `{code}`", parse_mode="Markdown")
        return

    if state == "admin_add_video" and message.video:
        bot.send_message(ADMIN_ID, f"📬 **Foydalanuvchidan shaxsiy kino:**\nKimdan: @{message.from_user.username} ({user_id})")
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.reply_to(message, "✅ Kino adminga yuborildi!")
        user_states.pop(user_id, None)
        return

    code = text.strip()
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
            bot.send_message(message.chat.id, "💎 Bu kino faqat **VIP foydalanuvchilar** uchun mo'ljallangan!", reply_markup=markup, parse_mode="Markdown")
            return
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE movies SET downloads = downloads + 1 WHERE code = ?', (code,))
        conn.commit()
        conn.close()
        new_downloads = downloads + 1

        caption = (
            f"🔥 ZAYAFKA KANALLARGA ZAKAZ OLAMAN!\n\n"
            f"Kanalga odam kerakmi? Unda yoz 👇\n"
            f"👥 Jivoy, aktiv auditoriya\n"
            f"⚡ Tez va sifatli ishlaymiz\n"
            f"💸 Narxlar hamyonbop\n"
            f"📈 Kanalni tezroq o'stirishga yordam beramiz\n\n"
            f"1000 ta zayafka — kelishilgan narxda ✅\n"
            f"Ko'p miqdorga alohida skidka bor 💥\n\n"
            f"📩 Zakaz uchun lichkaga yozing\n"
            f"@mhdnvwv\n\n"
            f"⬇️ Yuklab olingan: {new_downloads} ta"
        )
        bot.send_video(message.chat.id, video_id, caption=caption, parse_mode="Markdown", protect_content=True)
    else:
        menu_texts = ["🔍 Qidirish", "🎲 Tasodifiy", "💡 Kino tavsiya qilish", "📬 Shaxsiy kino qo'shish", "🎬 Admin orqali kino qo'shish", "💎 Premium Obuna", "📢 Reklama", "📊 Statistika", "🤖 Bot holati", "📢 Kanallarni sozlash", "🎬 Kino yuklash", "📢 Xabar yuborish (Reklama)"]
        if code not in menu_texts:
            bot.reply_to(message, f"❌ `{code}` kodi bo'yicha hech qanday kino topilmadi.", parse_mode="Markdown")

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
        
        bot.send_message(id_val, "🎉 Tabriklaymiz! VIP obunangiz admin tomonidan tasdiqlandi va faollashtirildi! ✅")
        show_main_menu(id_val, id_val)
        
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
    
