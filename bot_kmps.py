import telebot
from telebot import types
from groq import Groq
import sqlite3
import os
import re # Tambahan untuk pembersihan lebih bersih

# --- 1. KONFIGURASI ---
TELEGRAM_TOKEN = 'masukkan di sini token bot telegram kamu'
GROQ_API_KEY ='masukkan di sini api key groq kamu'
ID_KONSELOR = 'masukkan di sini id telegram konselor kamu'
LINK_TELEGRAM_KONSELOR = 'https://t.me/username_konselor'  # Ganti dengan username konselor kamu

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "konseling_kampus.db")

client_groq = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# --- 2. SETUP DATABASE ---
def init_db():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, kategori TEXT, reported INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, role TEXT, content TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. FUNGSI DATABASE ---
def get_user_data(user_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT kategori, reported FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchone()
    conn.close()
    return data

def update_user_kategori(user_id, kategori):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, kategori, reported) VALUES (?, ?, 0)", (user_id, kategori))
    c.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def save_chat(user_id, role, content):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()
    conn.close()

def get_history(user_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT role, content FROM history WHERE user_id = ? ORDER BY id ASC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in rows]

def get_message_count(user_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM history WHERE user_id = ? AND role = 'user'", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def set_reported(user_id):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE users SET reported = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- 4. HANDLERS ---
@bot.message_handler(commands=['start', 'reset'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('🎓 Akademik', '🏠 Pribadi', '💰 Keuangan', '💼 Karir')
    bot.send_message(message.chat.id, "Halo! Sesi konseling dimulai. Pilih kategori masalahmu:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ['🎓 Akademik', '🏠 Pribadi', '💰 Keuangan', '💼 Karir'])
def category_selected(message):
    update_user_kategori(message.chat.id, message.text)
    bot.send_message(message.chat.id, f"Kategori **{message.text}** dipilih. Silakan ceritakan masalahmu...", parse_mode='Markdown', reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: True)
def main_chat(message):
    user_id = message.chat.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        bot.send_message(user_id, "Silakan pilih kategori melalui menu /start")
        return

    kategori, has_reported = user_data
    
    instruksi_ai = (
        f"Kamu adalah konselor kampus. Fokus HANYA pada kategori: {kategori}. "
        "Jika user bertanya di luar masalah konseling kampus atau di luar kategori tersebut, "
        "jawablah dengan sopan bahwa kamu tidak bisa membantu topik tersebut. "
        "PENTING: Di baris terakhir jawabanmu, wajib tulis [STATUS: TINGGI] atau [STATUS: NORMAL]."
    )
    
    try:
        save_chat(user_id, "user", message.text)
        riwayat = get_history(user_id)
        
        completion = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": instruksi_ai}] + riwayat
        )
        
        jawaban_full = completion.choices[0].message.content
        
        # 1. Deteksi Status Urgensi
        status_urgensi = "🔴 TINGGI" if "STATUS: TINGGI" in jawaban_full.upper() else "🟢 NORMAL"
        
        # 2. Pembersihan Status Secara Agresif (agar tidak muncul di chat user)
        # Menghapus variasi: [STATUS: NORMAL], STATUS: NORMAL, status: normal, dll.
        clean_res = re.sub(r'\[?STATUS:\s*(TINGGI|NORMAL)\]?', '', jawaban_full, flags=re.IGNORECASE).strip()

        save_chat(user_id, "assistant", clean_res)
        
        # 3. Tambahkan Link Kontak hanya di pesan ke-5
        jumlah_pesan = get_message_count(user_id)
        if jumlah_pesan == 5:
            clean_res += (
                "\n\n---\n💡 *Saran Konselor:*\n"
                "Jika ingin berdiskusi lebih pribadi denganku, "
                f"silakan hubungi di sini: [Klik untuk Chat Telegram]({'https://t.me/username_konselor'})"
            )

        # 4. SAFETY SEND: Solusi Error 400
        try:
            # Coba kirim dengan Markdown
            bot.send_message(user_id, clean_res, parse_mode='Markdown', disable_web_page_preview=True)
        except Exception:
            # Jika gagal (Error 400), kirim tanpa Markdown (Teks Biasa) agar bot tidak macet
            bot.send_message(user_id, clean_res, disable_web_page_preview=True)

        # 5. Laporan ke Konselor (Hanya sekali)
        if has_reported == 0:
            link_mhs = f"tg://user?id={user_id}"
            laporan = (f"🚨 *KONSULTASI MASUK*\n👤: [{message.from_user.first_name}]({link_mhs})\n📁: {kategori}\n🧠: {status_urgensi}")
            bot.send_message(ID_KONSELOR, laporan, parse_mode='Markdown')
            set_reported(user_id)

    except Exception as e:
        print(f"Error Global: {e}")
        bot.send_message(user_id, "Maaf, sistem sedang sibuk.")

print("Bot Aktif dengan Safety Mode!")
bot.infinity_polling()