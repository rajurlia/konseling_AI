# Kecerdasan Buatan
tugas kelompok 8

# 🎓 Campus Counseling Bot (AI-Powered)

Bot Telegram yang dirancang sebagai asisten awal konseling mahasiswa menggunakan model **Llama-3.1-8b-instant** melalui Groq Cloud API.

## 🚀 Fitur Utama
- **Categorized Counseling:** Pilihan kategori masalah khusus (Akademik, Karir, Keuangan, Pribadi).
- **Session Management:** Penyimpanan riwayat percakapan menggunakan SQLite untuk konteks AI yang lebih baik.
- **Auto-Intervention:** Menawarkan bantuan konselor manusia secara otomatis pada pertukaran pesan ke-5.
- **Urgency Detection:** Menganalisis tingkat keparahan masalah mahasiswa (NORMAL/TINGGI) di setiap akhir sesi.
- **Real-time Reporting:** Notifikasi instan ke Telegram Konselor mencakup data mahasiswa dan ringkasan masalah.

## 🛠️ Teknologi yang Digunakan
- **Python** (Telebot/pyTelegramBotAPI)
- **Groq AI SDK** (Model: Llama-3.1-8b-instant)
- **SQLite3** (Local database management)
- **Regex** (Data cleaning & status filtering)

## 📋 Prasyarat
- Python 3.x
- Telegram Bot Token (dari @BotFather)
- Groq API Key
- ID konselor (dari @userinfo3bot)
1. Clone repository:
   ```bash
   git clone [https://github.com/username/campus-counseling-bot.git](https://github.com/username/campus-counseling-bot.git)
