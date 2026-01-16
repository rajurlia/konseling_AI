import telebot
from telebot import types
from groq import Groq
import sqlite3

# --- KONFIGURASI ---
TELEGRAM_TOKEN = 'masukkan di sini token bot telegram kamu'
GROQ_API_KEY ='masukkan di sini api key groq kamu'
ID_KONSELOR = 'masukkan di sini id telegram konselor kamu'
LINK_TELEGRAM_KONSELOR = 'https://t.me/username_konselor'

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
bot.delete_my_commands()

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('counseling.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY, status TEXT, category TEXT, count INTEGER, history TEXT)''')
    conn.commit()
    return conn

conn = init_db()

def get_user_data(user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return cursor.fetchone()

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("/start", "/reset", "/help", "/stop")
    return markup

def category_markup():
    markup = types.InlineKeyboardMarkup()
    btns = [
        types.InlineKeyboardButton("💼 Karir", callback_data="karir"),
        types.InlineKeyboardButton("🎓 Akademik", callback_data="akademik"),
        types.InlineKeyboardButton("💰 Keuangan", callback_data="keuangan"),
        types.InlineKeyboardButton("🧠 Pribadi", callback_data="pribadi")
    ]
    for btn in btns: markup.add(btn)
    return markup

# --- HANDLERS ---

@bot.message_handler(commands=['start', 'reset'])
def send_welcome(message):
    cursor = conn.cursor()
    # Reset atau buat baru data user
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, 'choosing', '', 0, ''))
    conn.commit()

    bot.send_message(
        message.chat.id,
        f"Halo {message.from_user.first_name}, selamat datang di layanan konseling.\nSilahkan pilih kategori masalahmu:",
        reply_markup=category_markup()
    )

@bot.message_handler(commands=['help'])
def help_info(message):
    text = ("📌 **Bantuan:**\n"
            "/start - Mulai konseling\n"
            "/reset - Mulai sesi baru (hapus riwayat)\n"
            "/stop - Akhiri sesi & lapor konselor\n")
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def set_category(call):
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'active', category = ? WHERE id = ?", (call.data, call.from_user.id))
    conn.commit()
    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"Kategori {call.data.upper()} aktif. Silahkan ceritakan masalahmu.",
                          call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['stop'])
def stop_session(message):
    data = get_user_data(message.from_user.id)
    if not data or data[1] == 'stopped':
        bot.reply_to(message, "Sesi sudah berhenti. Klik /start untuk mulai lagi.")
        return

    # Hitung urgensi sederhana
    urgency = "TINGGI" if any(w in data[4].lower() for w in ['parah', 'depresi', 'menyerah', 'darurat']) else "NORMAL"

    # Kirim Laporan ke Konselor (Sekali saja)
    user_mention = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
    report = (f"📋 **LAPORAN KONSELING**\n\n"
              f"👤 User: {user_mention}\n"
              f"🗂 Kategori: {data[2].upper()}\n"
              f"🚨 Urgensi: {urgency}")

    bot.send_message(ID_KONSELOR, report, parse_mode="Markdown")

    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'stopped' WHERE id = ?", (message.from_user.id,))
    conn.commit()
    bot.send_message(message.chat.id, "Sesi berhenti. Laporan telah terkirim. Terima kasih.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def chat_ai(message):
    data = get_user_data(message.from_user.id)

    if not data or data[1] == 'stopped':
        bot.reply_to(message, "Silahkan klik /start untuk memulai konseling.")
        return

    if data[1] == 'choosing':
        bot.reply_to(message, "Pilih kategori dulu ya di pesan atas.")
        return

    # Update counter pesan
    new_count = data[3] + 1
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET count = ? WHERE id = ?", (new_count, message.from_user.id))
    conn.commit()

    # Pesan ke-5: Kasih Link Konselor
    if new_count == 5:
        link = f"https://t.me/username_konselor"
        bot.send_message(message.chat.id, f"Jika butuh bantuan lebih lanjut, silakan hubungi [Konselor Kami]({link})", parse_mode="Markdown")

    # Panggil Groq AI
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": f"Kamu adalah konselor ahli {data[2]}. Gunakan bahasa Indonesia yang empati. Hanya jawab seputar konseling dan kategori {data[2]} Jika user bertanya di luar masalah konseling kampus atau di luar kategori tersebut,"
        "jawablah dengan sopan bahwa kamu tidak bisa membantu topik tersebut."},
                {"role": "user", "content": message.text}
            ]
        )
        response_text = completion.choices[0].message.content

        # Simpan history
        new_history = data[4] + f" User: {message.text} | AI: {response_text}"
        cursor.execute("UPDATE users SET history = ? WHERE id = ?", (new_history, message.from_user.id))
        conn.commit()

        bot.reply_to(message, response_text)
    except Exception as e:
        print(f"Error AI: {e}")
        bot.reply_to(message, "Maaf, sistem AI sedang sibuk. Coba lagi sebentar lagi.")

if __name__ == "__main__":
    print("Bot Konseling Berjalan...")
    bot.infinity_polling()