# tüm veriler json'da (admin ıd vs.)

import json
import urllib.request
import urllib.parse
import io
import datetime
import os
import ssl
import threading
from flask import Flask
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot Aktif ve Calisiyor!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_web, daemon=True).start()

# tokenler + api
TOKEN = "8649096143:AAGfsF6cKs7iaQrAe960_esFukkTu8BlbaI"
LOG_BOT_TOKEN = "8575651226:AAFEuEkgpzFBmqqYn5lHchoyYDhBRSZC6OY"
LOG_CHAT_IDS = ["7608508437", "7992717101"]

KATILMA_LISTESI = "https://t.me/addlist/BEBuMYh-In8yZjM0"
VIP_KANAL = "@librasystemvipsatis"
VIP_KANAL_LINK = "https://t.me/librasystemvipsatis"
LIBRA_BIO_LINK = "https://t.me/Librabio"

API_ADRES   = "https://freegamescor.online/apis/lenus/aile.php?tc={}"
API_SULALE  = "https://freegamescor.online/apis/lenus/sulale.php?tc={}"
API_GSM     = "https://freegamescor.online/apis/lenus/gsm.php?tc={}"
API_ADSOYAD = "https://freegamescor.online/apis/lenus/adsoyad.php?ad={}&soyad={}"
API_TCPRO   = "https://freegamescor.online/apis/lenus/tcpro.php?tc={}"
API_ISYERI  = "https://freegamescor.online/apis/lenus/isyeri.php?tc={}"
API_OKUL    = "https://freegamescor.online/apis/lenus/okul.php?tc={}"

GUNLUK_SORGU_HAKKI = 10
KULLANICI_DOSYA = "kullanicilar.json"
ADMIN_DOSYA = "admin.json"
INFO_DOSYA = "info.json"
DAVET_DOSYA = "davetler.json"
VIP_TALEP_DOSYA = "vip_talepler.json"

ssl._create_default_https_context = ssl._create_unverified_context


# veri t. fonksiyonlar

def veritabani_yukle(dosya):
    if os.path.exists(dosya):
        try:
            with open(dosya, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {}
    return {}


def veritabani_kaydet(dosya, veritabani):
    try:
        with open(dosya, "w", encoding="utf-8") as f:
            json.dump(veritabani, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Veritabani kaydetme hatasi: {e}")


def info_guncelle(veritabani, user_id, username, first_name):
    info = veritabani_yukle(INFO_DOSYA)
    user_id_str = str(user_id)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_id_str not in info:
        info[user_id_str] = {
            "username": username,
            "first_name": first_name,
            "katilma_tarihi": now,
            "son_giris": now,
            "toplam_sorgu": 0
        }
    else:
        info[user_id_str]["son_giris"] = now
        info[user_id_str]["username"] = username
        info[user_id_str]["first_name"] = first_name

    veritabani_kaydet(INFO_DOSYA, info)


def info_sorgu_artir(user_id):
    info = veritabani_yukle(INFO_DOSYA)
    user_id_str = str(user_id)

    if user_id_str in info:
        info[user_id_str]["toplam_sorgu"] = info[user_id_str].get("toplam_sorgu", 0) + 1
        veritabani_kaydet(INFO_DOSYA, info)


def admin_mi(user_id):
    adminler = veritabani_yukle(ADMIN_DOSYA)
    return str(user_id) in adminler


def kullanici_getir(veritabani, user_id):
    user_id_str = str(user_id)

    if user_id_str not in veritabani:
        veritabani[user_id_str] = {
            "sorgu_hakki": GUNLUK_SORGU_HAKKI,
            "son_sorgu_tarihi": datetime.datetime.now().strftime("%Y-%m-%d"),
            "referans_sayisi": 0,
            "vip": False,
            "ban": False,
            "all_hak": 0,
            "davet_sayisi": 0,
            "davet_edilenler": [],
            "vip_bitis_tarihi": None,
            "vip_tipi": None
        }
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    return veritabani[user_id_str]


def sorgu_hakki_kontrol(veritabani, user_id):
    kullanici = kullanici_getir(veritabani, user_id)
    bugun = datetime.datetime.now().strftime("%Y-%m-%d")

    if kullanici["son_sorgu_tarihi"] != bugun:
        kullanici["sorgu_hakki"] = GUNLUK_SORGU_HAKKI
        kullanici["all_hak"] = 0
        kullanici["son_sorgu_tarihi"] = bugun
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    toplam_hak = kullanici["sorgu_hakki"] + kullanici.get("all_hak", 0)
    return toplam_hak


def sorgu_hakki_dusur(veritabani, user_id):
    kullanici = kullanici_getir(veritabani, user_id)

    if kullanici.get("all_hak", 0) > 0:
        kullanici["all_hak"] -= 1
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)
        return True

    if kullanici["sorgu_hakki"] > 0:
        kullanici["sorgu_hakki"] -= 1
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)
        return True

    return False


def vip_kontrol(veritabani, user_id):
    kullanici = kullanici_getir(veritabani, user_id)

    if not kullanici.get("vip", False):
        return False

    if kullanici.get("vip_tipi") == "sinirsiz":
        return True

    if kullanici.get("vip_bitis_tarihi"):
        try:
            bitis = datetime.datetime.strptime(kullanici["vip_bitis_tarihi"], "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() > bitis:
                kullanici["vip"] = False
                kullanici["vip_tipi"] = None
                kullanici["vip_bitis_tarihi"] = None
                kullanici["sorgu_hakki"] = GUNLUK_SORGU_HAKKI
                veritabani_kaydet(KULLANICI_DOSYA, veritabani)
                return False
        except:
            pass

    return True


# davet sistemi
def davet_kaydet(davet_eden_id, davet_edilen_id, davet_edilen_username, davet_edilen_first_name):
    davetler = veritabani_yukle(DAVET_DOSYA)
    davet_eden_str = str(davet_eden_id)
    davet_edilen_str = str(davet_edilen_id)

    if davet_eden_str not in davetler:
        davetler[davet_eden_str] = {
            "davet_edilenler": [],
            "toplam_davet": 0
        }

    if davet_edilen_str not in [d["user_id"] for d in davetler[davet_eden_str]["davet_edilenler"]]:
        davetler[davet_eden_str]["davet_edilenler"].append({
            "user_id": davet_edilen_str,
            "username": davet_edilen_username,
            "first_name": davet_edilen_first_name,
            "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        davetler[davet_eden_str]["toplam_davet"] += 1
        veritabani_kaydet(DAVET_DOSYA, davetler)

        kullanici_db = veritabani_yukle(KULLANICI_DOSYA)
        kullanici = kullanici_getir(kullanici_db, davet_eden_id)
        kullanici["davet_sayisi"] = davetler[davet_eden_str]["toplam_davet"]
        if davet_edilen_str not in kullanici.get("davet_edilenler", []):
            kullanici["davet_edilenler"].append(davet_edilen_str)
        veritabani_kaydet(KULLANICI_DOSYA, kullanici_db)

        return True
    return False


def davet_bilgisi_getir(user_id):
    davetler = veritabani_yukle(DAVET_DOSYA)
    davet_eden_str = str(user_id)

    if davet_eden_str not in davetler:
        return 0, []

    return davetler[davet_eden_str].get("toplam_davet", 0), davetler[davet_eden_str].get("davet_edilenler", [])


def vip_odul_kontrol(davet_sayisi):
    if davet_sayisi >= 1000:
        return "sinirsiz", "SINIRSIZ VIP"
    elif davet_sayisi >= 200:
        return "1ay", "1 AY VIP"
    elif davet_sayisi >= 50:
        return "1hafta", "1 HAFTA VIP"
    return None, None


def vip_talep_kaydet(user_id, username, first_name, davet_sayisi, vip_tipi, vip_isim):
    talepler = veritabani_yukle(VIP_TALEP_DOSYA)
    user_id_str = str(user_id)

    talepler[user_id_str] = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "davet_sayisi": davet_sayisi,
        "istenen_vip_tipi": vip_tipi,
        "istenen_vip_isim": vip_isim,
        "talep_tarihi": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "durum": "beklemede"
    }
    veritabani_kaydet(VIP_TALEP_DOSYA, talepler)


# log kaydı 

def log_gonder(kullanici_adi, kullanici_id, islem, yapilan_islem):
    try:
        import telegram
        log_bot = telegram.Bot(token=LOG_BOT_TOKEN)
        zaman = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        log_mesaj = (
            f"🆕 YENI SORGU\n\n"
            f"👤 Kullanici Adi: @{kullanici_adi}\n"
            f"🆔 Kullanici ID: {kullanici_id}\n"
            f"🔧 Islem: {islem}\n"
            f"📋 Yapilan Islem: {yapilan_islem}\n"
            f"⏰ Zaman: {zaman}"
        )

        for chat_id in LOG_CHAT_IDS:
            try:
                log_bot.send_message(chat_id=int(chat_id), text=log_mesaj)
            except Exception as e:
                print(f"❌ Log gonderme hatasi ({chat_id}): {e}")

    except Exception as e:
        print(f"❌ Log bot hatasi: {e}")


def txt_dosya_gonder(update, context, icerik, dosya_adi="sonuc.txt"):
    try:
        chat_id = update.effective_chat.id
        txt_buffer = io.BytesIO()
        txt_buffer.write(icerik.encode('utf-8'))
        txt_buffer.seek(0)

        context.bot.send_document(
            chat_id=chat_id,
            document=txt_buffer,
            filename=dosya_adi
        )
        return True
    except Exception as e:
        print(f"❌ Dosya gonderme hatasi: {e}")
        return False


# kanal kontrol (burada sıkıntı olabilir)

def kanal_kontrol(update, context, user_id):
    zorunlu_kanallar = [
        "@LibraSystemChat",
        "@LibraSystemDuyuru",
        "@LibraSystemsGiris",
        "@librasystemfast"
    ]

    eksik_kanallar = []

    for kanal in zorunlu_kanallar:
        try:
            member = context.bot.get_chat_member(chat_id=kanal, user_id=user_id)
            if member.status in ['left', 'kicked']:
                eksik_kanallar.append(kanal)
        except Exception as e:
            print(f"⚠️ Kanal kontrol hatasi ({kanal}): {e}")
            pass

    return eksik_kanallar


def kanal_mesaji_gonder(update):
    butonlar = [[InlineKeyboardButton("🔥 TUM KANALLARA KATIL", url=KATILMA_LISTESI)]]
    klavye = InlineKeyboardMarkup(butonlar)

    mesaj = (
        "⚠️ Kanal Kontrolu\n\n"
        "Botu kullanabilmek icin zorunlu kanallara katilmaniz gerekiyor!\n\n"
        "📌 Asagidaki butona basarak tum kanallari tek seferde gorup katilabilirsiniz.\n"
        "✅ Katildiktan sonra tekrar /start yazin."
    )

    update.message.reply_text(mesaj, reply_markup=klavye)


# baslangiç
def hosgeldin_menusu_gonder(update, context, veritabani):
    user = update.message.from_user
    username = user.username or "Kullanici"
    user_id = user.id
    first_name = user.first_name or "Isimsiz"

    info_guncelle(veritabani, user_id, username, first_name)

    kalan_hak = sorgu_hakki_kontrol(veritabani, user_id)

    vip_kontrol(veritabani, user_id)
    kullanici = kullanici_getir(veritabani, user_id)

    davet_sayisi, _ = davet_bilgisi_getir(user_id)
    vip_durum = "💎 VIP" if kullanici.get("vip", False) else "🆓 Ucretsiz"

    butonlar = [
        [
            InlineKeyboardButton("📋 Komutlar", callback_data="komutlar"),
            InlineKeyboardButton("🔗 LIBRA", url=LIBRA_BIO_LINK)
        ],
        [
            InlineKeyboardButton("⭐ Sorgu Hakki Kazan", callback_data="sorgu_hakki"),
            InlineKeyboardButton("💎 VIP satin Al", url=VIP_KANAL_LINK)
        ],
        [
            InlineKeyboardButton("❓ Nasil Kullanilir", callback_data="nasil_kullanilir")
        ],
        [
            InlineKeyboardButton("🔗 Referans Linkin", callback_data="referans_link")
        ],
        [
            InlineKeyboardButton("🎁 Davet Odulleri", callback_data="invite_gifts")
        ]
    ]

    klavye = InlineKeyboardMarkup(butonlar)

    mesaj = (
        f"👋 Hosgeldin, @{username}\n\n"
        f"🆔 Kullanici ID: {user_id}\n"
        f"🔍 Gunluk Sorgu Hakkin: {kalan_hak}\n"
        f"🔄 Her gun 00:00'da yenilenir\n"
        f"📨 Toplam Davet: {davet_sayisi}\n"
        f"{vip_durum}\n\n"
        f"⬇️ Asagidaki butonlari kullanabilirsin."
    )

    update.message.reply_text(mesaj, reply_markup=klavye)


def referans_link_callback(update, context):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    bot_username = context.bot.username
    referans_link = f"https://t.me/{bot_username}?start={user_id}"

    mesaj = (
        "🔗 REFERANS LINKIN\n\n"
        f"Senin referans linkin:\n"
        f"`{referans_link}`\n\n"
        f"📢 Bu linki arkadaslarinla paylas!\n"
        f"✅ Her kayit olan kullanici icin +5 sorgu hakki kazanabilirsin.\n\n"
        f"📌 Linki kopyalamak icin uzerine basili tut."
    )

    butonlar = [[InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=mesaj, reply_markup=klavye, parse_mode="Markdown")


def komutlar_callback(update, context):
    query = update.callback_query
    query.answer()

    komutlar_mesaj = (
        "📋 KULLANILABILIR KOMUTLAR\n\n"
        "➱ /adres 41xxxxxxxxxx\n"
        "➱ /tcgsm 41xxxxxxxxxx\n"
        "➱ /sulale 41xxxxxxxxxx\n"
        "➱ /tcpro 41xxxxxxxxxx\n"
        "➱ /adsoyad mehmet demir\n"
        "➱ /isyeri 41xxxxxxxxxx\n"
        "➱ /okul 41xxxxxxxxxx\n\n"
        "📝 2 isimli kisiler icin:\n"
        "➱ /adsoyad mehmet akif ersoy\n\n"
        "✨ Ekstra:\n"
        "➱ /davetlerim - Davet istatistiklerin\n"
        "➱ /vipodul - VIP odul talep et\n\n"
        "<< Geri donmek icin /start yazin."
    )

    butonlar = [[InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=komutlar_mesaj, reply_markup=klavye)


def nasil_kullanilir_callback(update, context):
    query = update.callback_query
    query.answer()

    nasil_mesaj = (
        "❓ NASIL KULLANILIR\n\n"
        "➱ /adres <TC>\n"
        "   ➜ TC numarasi ile adres bilgisi sorgular\n"
        "   📝 Ornek: /adres 12345678901\n\n"
        "➱ /tcgsm <TC>\n"
        "   ➜ TC numarasi ile GSM numarasi sorgular\n"
        "   📝 Ornek: /tcgsm 12345678901\n\n"
        "➱ /adsoyad <Ad> <Soyad>\n"
        "   ➜ Ad ve soyad ile kisi sorgular\n"
        "   📝 Ornek: /adsoyad mehmet demir\n"
        "   📝 2 isimli: /adsoyad mehmet akif ersoy\n\n"
        "➱ /sulale <TC>\n"
        "   ➜ TC ile aile/sulale bilgisi sorgular\n"
        "   📝 Ornek: /sulale 12345678901\n\n"
        "➱ /tcpro <TC>\n"
        "   ➜ TC ile detayli profil sorgular\n"
        "   📝 Ornek: /tcpro 12345678901\n\n"
        "➱ /isyeri <TC>\n"
        "   ➜ TC ile is yeri bilgisi sorgular\n"
        "   📝 Ornek: /isyeri 12345678901\n\n"
        "➱ /okul <TC>\n"
        "   ➜ TC ile okul bilgisi sorgular\n"
        "   📝 Ornek: /okul 12345678901\n\n"
        "<< Geri donmek icin /start yazin."
    )

    butonlar = [[InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=nasil_mesaj, reply_markup=klavye)


def sorgu_hakki_callback(update, context):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    bot_username = context.bot.username
    referans_link = f"https://t.me/{bot_username}?start={user_id}"

    mesaj = (
        "⭐ SORGU HAKKI KAZAN\n\n"
        f"🔍 Gunluk sorgu hakkin: {GUNLUK_SORGU_HAKKI}\n"
        f"🔄 Her gun 00:00'da otomatik yenilenir\n\n"
        "💡 Daha fazla sorgu hakki icin:\n\n"
        f"1️⃣ Referans linkini paylas:\n"
        f"`{referans_link}`\n"
        f"   ✅ Her kayit olan +5 sorgu hakki\n\n"
        f"2️⃣ VIP uyelik al:\n"
        f"   💎 {VIP_KANAL}\n\n"
        "<< Geri donmek icin /start yazin."
    )

    butonlar = [[InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=mesaj, reply_markup=klavye, parse_mode="Markdown")


def invite_gifts_callback(update, context):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    davet_sayisi, davet_edilenler = davet_bilgisi_getir(user_id)

    mevcut_odul = ""
    vip_tipi, vip_isim = vip_odul_kontrol(davet_sayisi)
    if vip_tipi:
        mevcut_odul = f"\n\n🎉 Senin mevcut odul hakkin: {vip_isim}"

    mesaj = (
        "🎁 Libra Sorgu Botu - Davet Odulleri\n"
        "═══════════════════════\n\n"
        f"📨 Senin Toplam Davetin: {davet_sayisi}\n\n"
        "🏆 ODUL SISTEMI:\n"
        "═══════════════════════\n"
        "📆 50x Davet = 1 Hafta VIP\n"
        "📅 200x Davet = 1 Ay VIP\n"
        "♾️ 1000x Davet = Sinirsiz VIP\n"
        "═══════════════════════\n\n"
        "✅ Sartlari karsilayan kisiler\n"
        "   adminlere ulasabilir."
        f"{mevcut_odul}\n\n"
        "💡 VIP odulunu talep etmek icin\n"
        "   /vipodul yaz."
    )

    butonlar = [
        [InlineKeyboardButton("📋 Davetlerimi Gor", callback_data="davetlerim_detay")],
        [InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]
    ]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=mesaj, reply_markup=klavye)


def davetlerim_detay_callback(update, context):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    davet_sayisi, davet_edilenler = davet_bilgisi_getir(user_id)

    mesaj = f"📋 DAVET ISTATISTIKLERIN\n\n"
    mesaj += f"📨 Toplam Davet: {davet_sayisi}\n"
    mesaj += f"👥 Davet Edilen Kisi Sayisi: {len(davet_edilenler)}\n\n"

    if davet_edilenler:
        mesaj += "📋 Davet Ettigin Kisiler:\n"
        mesaj += "═══════════════════════\n"
        for i, davet in enumerate(davet_edilenler[-20:], 1):
            isim = davet.get("first_name", "Bilinmiyor")
            username = davet.get("username", "Yok")
            tarih = davet.get("tarih", "Bilinmiyor")
            mesaj += f"{i}. {isim} (@{username}) - {tarih}\n"
    else:
        mesaj += "😕 Henuz hicbir kisi davet etmedin.\n"
        mesaj += "🔗 Referans linkini paylas ve\n"
        mesaj += "   arkadaslarini davet et!"

    butonlar = [
        [InlineKeyboardButton("🎁 Davet Odulleri", callback_data="invite_gifts")],
        [InlineKeyboardButton("<< Geri Don", callback_data="geri_don")]
    ]
    klavye = InlineKeyboardMarkup(butonlar)

    query.edit_message_text(text=mesaj, reply_markup=klavye)


def geri_don_callback(update, context):
    query = update.callback_query
    query.answer()

    user = query.from_user
    username = user.username or "Kullanici"
    user_id = user.id

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    kalan_hak = sorgu_hakki_kontrol(veritabani, user_id)

    vip_kontrol(veritabani, user_id)
    kullanici = kullanici_getir(veritabani, user_id)

    davet_sayisi, _ = davet_bilgisi_getir(user_id)
    vip_durum = "💎 VIP" if kullanici.get("vip", False) else "🆓 Ucretsiz"

    butonlar = [
        [
            InlineKeyboardButton("📋 Komutlar", callback_data="komutlar"),
            InlineKeyboardButton("🔗 LIBRA", url=LIBRA_BIO_LINK)
        ],
        [
            InlineKeyboardButton("⭐ Sorgu Hakki Kazan", callback_data="sorgu_hakki"),
            InlineKeyboardButton("💎 VIP satin Al", url=VIP_KANAL_LINK)
        ],
        [
            InlineKeyboardButton("❓ Nasil Kullanilir", callback_data="nasil_kullanilir")
        ],
        [
            InlineKeyboardButton("🔗 Referans Linkin", callback_data="referans_link")
        ],
        [
            InlineKeyboardButton("🎁 Davet Odulleri", callback_data="invite_gifts")
        ]
    ]

    klavye = InlineKeyboardMarkup(butonlar)

    mesaj = (
        f"👋 Hosgeldin, @{username}\n\n"
        f"🆔 Kullanici ID: {user_id}\n"
        f"🔍 Gunluk Sorgu Hakkin: {kalan_hak}\n"
        f"🔄 Her gun 00:00'da yenilenir\n"
        f"📨 Toplam Davet: {davet_sayisi}\n"
        f"{vip_durum}\n\n"
        f"⬇️ Asagidaki butonlari kullanabilirsin."
    )

    query.edit_message_text(text=mesaj, reply_markup=klavye)


# komutlar

def davetlerim(update, context):
    user_id = update.message.from_user.id
    davet_sayisi, davet_edilenler = davet_bilgisi_getir(user_id)

    mesaj = f"📋 DAVET ISTATISTIKLERIN\n\n"
    mesaj += f"📨 Toplam Davet: {davet_sayisi}\n"
    mesaj += f"👥 Davet Edilen Kisi Sayisi: {len(davet_edilenler)}\n\n"

    if davet_edilenler:
        mesaj += "📋 Davet Ettigin Kisiler:\n"
        mesaj += "═══════════════════════\n"
        for i, davet in enumerate(davet_edilenler[-20:], 1):
            isim = davet.get("first_name", "Bilinmiyor")
            username = davet.get("username", "Yok")
            tarih = davet.get("tarih", "Bilinmiyor")
            mesaj += f"{i}. {isim} (@{username}) - {tarih}\n"
    else:
        mesaj += "😕 Henuz hicbir kisi davet etmedin.\n"
        mesaj += "🔗 Referans linkini paylas ve\n"
        mesaj += "   arkadaslarini davet et!\n\n"
        mesaj += f"🔗 Linkin: https://t.me/{context.bot.username}?start={user_id}"

    update.message.reply_text(mesaj)


def vipodul(update, context):
    user_id = update.message.from_user.id
    user = update.message.from_user
    username = user.username or "Kullanici"
    first_name = user.first_name or "Isimsiz"

    davet_sayisi, _ = davet_bilgisi_getir(user_id)
    vip_tipi, vip_isim = vip_odul_kontrol(davet_sayisi)

    if not vip_tipi:
        mesaj = (
            "🎁 VIP ODUL TALEP\n\n"
            f"📨 Toplam Davetin: {davet_sayisi}\n\n"
            "😕 Maalesef henuz bir odul hakki kazanamadin.\n\n"
            "🏆 ODUL SISTEMI:\n"
            "═══════════════════════\n"
            "📆 50x Davet = 1 Hafta VIP\n"
            "📅 200x Davet = 1 Ay VIP\n"
            "♾️ 1000x Davet = Sinirsiz VIP\n"
            "═══════════════════════\n\n"
            "💪 Daha fazla davet yap ve odul kazan!"
        )
        update.message.reply_text(mesaj)
        return

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    kullanici = kullanici_getir(veritabani, user_id)

    if kullanici.get("vip", False):
        update.message.reply_text("⚠️ Zaten VIP uyeligin bulunuyor!\nYeni bir odul talep edemezsin.")
        return

    vip_talep_kaydet(user_id, username, first_name, davet_sayisi, vip_tipi, vip_isim)

    mesaj = (
        "🎁 VIP ODUL TALEBI\n\n"
        f"📨 Toplam Davetin: {davet_sayisi}\n"
        f"🎉 Talep Edilen Odul: {vip_isim}\n\n"
        "✅ Talebiniz adminlere iletildi!\n"
        "⏳ Onaylandiginda size bildirilecektir.\n\n"
        f"💎 VIP kanalimiz: {VIP_KANAL}"
    )
    update.message.reply_text(mesaj)


# burası sabit (admin komutları)
def admin_panel(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Bu komuta yetkiniz yok!")
        return

    mesaj = (
        "🔐 ADMIN PANELI\n\n"
        "📋 Komutlar:\n"
        "🔹 /ban <user_id> - Kullanici banla\n"
        "🔹 /unban <user_id> - Ban kaldir\n"
        "🔹 /hak <user_id> <sayi> - Sorgu hakki ver\n"
        "🔹 /all <sayi> - HERKESE sorgu hakki ver\n"
        "🔹 /vip <user_id> - VIP yap\n"
        "🔹 /normal <user_id> - VIP kaldir\n"
        "🔹 /stats - Bot istatistikleri\n"
        "🔹 /list - Kullanici listesi\n"
        "🔹 /info - Detayli info.json raporu\n"
        "🔹 /viptalepler - Bekleyen VIP talepleri\n"
        "🔹 /viponayla <user_id> - VIP talebini onayla\n"
        "🔹 /vipreddet <user_id> - VIP talebini reddet\n"
        "🔹 /davetsiralama - En cok davet edenler"
    )

    update.message.reply_text(mesaj)


def admin_ban(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /ban <user_id>")
        return

    ban_user_id = context.args[0]
    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    if ban_user_id not in veritabani:
        veritabani[ban_user_id] = {
            "sorgu_hakki": 0,
            "son_sorgu_tarihi": datetime.datetime.now().strftime("%Y-%m-%d"),
            "referans_sayisi": 0,
            "vip": False,
            "ban": True,
            "all_hak": 0,
            "davet_sayisi": 0,
            "davet_edilenler": [],
            "vip_bitis_tarihi": None,
            "vip_tipi": None
        }
    else:
        veritabani[ban_user_id]["ban"] = True
        veritabani[ban_user_id]["sorgu_hakki"] = 0

    veritabani_kaydet(KULLANICI_DOSYA, veritabani)
    update.message.reply_text(f"✅ {ban_user_id} ID'li kullanici banlandi!")


def admin_unban(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /unban <user_id>")
        return

    unban_user_id = context.args[0]
    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    if unban_user_id in veritabani:
        veritabani[unban_user_id]["ban"] = False
        veritabani[unban_user_id]["sorgu_hakki"] = GUNLUK_SORGU_HAKKI
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)
        update.message.reply_text(f"✅ {unban_user_id} ID'li kullanicinin bani kaldirildi!")
    else:
        update.message.reply_text("❌ Kullanici bulunamadi!")


def admin_hak(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if len(context.args) < 2:
        update.message.reply_text("❓ Kullanim: /hak <user_id> <sayi>")
        return

    hedef_id = context.args[0]
    try:
        hak_sayisi = int(context.args[1])
    except ValueError:
        update.message.reply_text("⚠️ Sayisal deger girin!")
        return

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    kullanici = kullanici_getir(veritabani, int(hedef_id))
    kullanici["sorgu_hakki"] = hak_sayisi
    veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    update.message.reply_text(f"✅ {hedef_id} ID'li kullaniciya {hak_sayisi} sorgu hakki verildi!")


def admin_all(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /all <sayi>\n📝 Ornek: /all 100")
        return

    try:
        hak_sayisi = int(context.args[0])
    except ValueError:
        update.message.reply_text("⚠️ Sayisal deger girin!")
        return

    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    sayac = 0
    for uid in veritabani:
        veritabani[uid]["all_hak"] = hak_sayisi
        sayac += 1

    veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    update.message.reply_text(
        f"✅ TUM KULLANICILARA {hak_sayisi} ek sorgu hakki verildi!\n"
        f"👥 Etkilenen: {sayac} kullanici\n"
        f"🔄 Gun bitince otomatik sifirlanir (10'a doner)"
    )


def admin_vip(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /vip <user_id>")
        return

    vip_id = context.args[0]
    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    kullanici = kullanici_getir(veritabani, int(vip_id))
    kullanici["vip"] = True
    kullanici["vip_tipi"] = "sinirsiz"
    kullanici["vip_bitis_tarihi"] = None
    kullanici["sorgu_hakki"] = 999
    veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    update.message.reply_text(f"💎 {vip_id} ID'li kullanici VIP yapildi! (Sinirsiz)")


def admin_normal(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /normal <user_id>")
        return

    normal_id = context.args[0]
    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    if normal_id in veritabani:
        veritabani[normal_id]["vip"] = False
        veritabani[normal_id]["vip_tipi"] = None
        veritabani[normal_id]["vip_bitis_tarihi"] = None
        veritabani[normal_id]["sorgu_hakki"] = GUNLUK_SORGU_HAKKI
        veritabani[normal_id]["all_hak"] = 0
        veritabani_kaydet(KULLANICI_DOSYA, veritabani)
        update.message.reply_text(f"🆓 {normal_id} ID'li kullanici normal yapildi!")
    else:
        update.message.reply_text("❌ Kullanici bulunamadi!")


def admin_stats(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    info = veritabani_yukle(INFO_DOSYA)
    davetler = veritabani_yukle(DAVET_DOSYA)

    toplam_kullanici = len(veritabani)
    vip_sayisi = sum(1 for u in veritabani.values() if u.get("vip", False))
    banli_sayisi = sum(1 for u in veritabani.values() if u.get("ban", False))
    toplam_referans = sum(u.get("referans_sayisi", 0) for u in veritabani.values())
    toplam_sorgu = sum(i.get("toplam_sorgu", 0) for i in info.values())
    toplam_davet = sum(d.get("toplam_davet", 0) for d in davetler.values())

    mesaj = (
        "📊 BOT ISTATISTIKLERI\n\n"
        f"👥 Toplam kullanici: {toplam_kullanici}\n"
        f"💎 VIP kullanici: {vip_sayisi}\n"
        f"🚫 Banli kullanici: {banli_sayisi}\n"
        f"🔗 Toplam referans: {toplam_referans}\n"
        f"🔍 Toplam sorgu: {toplam_sorgu}\n"
        f"📨 Toplam davet: {toplam_davet}\n"
        f"📅 Tarih: {datetime.datetime.now().strftime('%d.%m.%Y')}"
    )

    update.message.reply_text(mesaj)


def admin_list(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    info = veritabani_yukle(INFO_DOSYA)

    mesaj = "📋 SON KULLANICILAR:\n\n"
    for uid, data in list(veritabani.items())[-10:]:
        vip = "💎 VIP" if data.get("vip") else "🆓 Ucretsiz"
        ban = "🚫 BANLI" if data.get("ban") else "✅ Aktif"
        hak = data.get("sorgu_hakki", 0) + data.get("all_hak", 0)
        davet = data.get("davet_sayisi", 0)

        isim = "Bilinmiyor"
        if uid in info:
            isim = info[uid].get("first_name", "Bilinmiyor")

        mesaj += f"{vip} | {ban} | {uid} ({isim}): {hak} hak | {davet} davet\n"

    update.message.reply_text(mesaj)


def admin_info(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    info = veritabani_yukle(INFO_DOSYA)
    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    vip_listesi = []
    for uid, data in veritabani.items():
        if data.get("vip", False):
            isim = info.get(uid, {}).get("first_name", "Bilinmiyor")
            username = info.get(uid, {}).get("username", "Yok")
            vip_tipi = data.get("vip_tipi", "Bilinmiyor")
            vip_listesi.append(f"💎 {uid} - @{username} ({isim}) [{vip_tipi}]")

    sorgu_siralama = sorted(info.items(), key=lambda x: x[1].get("toplam_sorgu", 0), reverse=True)[:5]

    mesaj = (
        "📊 INFO.JSON RAPORU\n\n"
        f"👥 Toplam kayitli kullanici: {len(info)}\n\n"
        f"💎 VIP LISTESI ({len(vip_listesi)} kisi):\n"
    )

    if vip_listesi:
        mesaj += "\n".join(vip_listesi) + "\n\n"
    else:
        mesaj += "VIP kullanici yok\n\n"

    mesaj += "🏆 EN COK SORGU YAPANLAR:\n"
    for uid, data in sorgu_siralama:
        isim = data.get("first_name", "Bilinmiyor")
        sorgu = data.get("toplam_sorgu", 0)
        mesaj += f"🔹 {isim}: {sorgu} sorgu\n"

    update.message.reply_text(mesaj)


def admin_vip_talepler(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    talepler = veritabani_yukle(VIP_TALEP_DOSYA)

    if not talepler:
        update.message.reply_text("📭 Bekleyen VIP talebi yok.")
        return

    mesaj = "🎁 BEKLEYEN VIP TALEPLERI\n\n"
    for uid, talep in talepler.items():
        if talep.get("durum") == "beklemede":
            mesaj += (
                f"🆔 ID: {uid}\n"
                f"   👤 Isim: {talep.get('first_name', 'Bilinmiyor')}\n"
                f"   🔗 Username: @{talep.get('username', 'Yok')}\n"
                f"   📨 Davet: {talep.get('davet_sayisi', 0)}\n"
                f"   🎉 Istinen: {talep.get('istenen_vip_isim', 'Bilinmiyor')}\n"
                f"   ⏰ Talep Tarihi: {talep.get('talep_tarihi', 'Bilinmiyor')}\n"
                f"═══════════════════════\n"
            )

    mesaj += "\n✅ /viponayla <user_id>\n❌ /vipreddet <user_id>"
    update.message.reply_text(mesaj)


def admin_vip_onayla(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /viponayla <user_id>")
        return

    hedef_id = context.args[0]
    talepler = veritabani_yukle(VIP_TALEP_DOSYA)

    if hedef_id not in talepler:
        update.message.reply_text("❌ Bu kullanicinin talebi bulunamadi!")
        return

    talep = talepler[hedef_id]
    vip_tipi = talep.get("istenen_vip_tipi")

    veritabani = veritabani_yukle(KULLANICI_DOSYA)
    kullanici = kullanici_getir(veritabani, int(hedef_id))

    kullanici["vip"] = True
    kullanici["vip_tipi"] = vip_tipi

    now = datetime.datetime.now()
    if vip_tipi == "1hafta":
        bitis = now + datetime.timedelta(days=7)
        kullanici["vip_bitis_tarihi"] = bitis.strftime("%Y-%m-%d %H:%M:%S")
        kullanici["sorgu_hakki"] = 999
    elif vip_tipi == "1ay":
        bitis = now + datetime.timedelta(days=30)
        kullanici["vip_bitis_tarihi"] = bitis.strftime("%Y-%m-%d %H:%M:%S")
        kullanici["sorgu_hakki"] = 999
    elif vip_tipi == "sinirsiz":
        kullanici["vip_bitis_tarihi"] = None
        kullanici["sorgu_hakki"] = 999

    veritabani_kaydet(KULLANICI_DOSYA, veritabani)

    talepler[hedef_id]["durum"] = "onaylandi"
    talepler[hedef_id]["onay_tarihi"] = now.strftime("%Y-%m-%d %H:%M:%S")
    veritabani_kaydet(VIP_TALEP_DOSYA, talepler)

    update.message.reply_text(
        f"✅ {hedef_id} ID'li kullanicinin\n"
        f"   VIP talebi onaylandi!\n"
        f"   🎉 Odul: {talep.get('istenen_vip_isim', 'Bilinmiyor')}"
    )

    try:
        context.bot.send_message(
            chat_id=int(hedef_id),
            text=(
                "🎉 TEBRIKLER!\n\n"
                f"💎 VIP talebiniz onaylandi!\n"
                f"🎁 Odulunuz: {talep.get('istenen_vip_isim', 'Bilinmiyor')}\n\n"
                "✅ Artik botu limitsiz kullanabilirsiniz!\n"
                f"💎 VIP kanalimiz: {VIP_KANAL}"
            )
        )
    except Exception as e:
        print(f"❌ Kullaniciya bildirim gonderilemedi: {e}")


def admin_vip_reddet(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    if not context.args:
        update.message.reply_text("❓ Kullanim: /vipreddet <user_id>")
        return

    hedef_id = context.args[0]
    talepler = veritabani_yukle(VIP_TALEP_DOSYA)

    if hedef_id not in talepler:
        update.message.reply_text("❌ Bu kullanicinin talebi bulunamadi!")
        return

    talepler[hedef_id]["durum"] = "reddedildi"
    talepler[hedef_id]["reddetme_tarihi"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    veritabani_kaydet(VIP_TALEP_DOSYA, talepler)

    update.message.reply_text(f"❌ {hedef_id} ID'li kullanicinin VIP talebi reddedildi.")

    try:
        context.bot.send_message(
            chat_id=int(hedef_id),
            text=(
                "❌ VIP TALEBINIZ REDDEDILDI\n\n"
                "😕 Maalesef VIP talebiniz reddedildi.\n"
                "📞 Daha fazla bilgi icin adminlerle iletisime gecin.\n"
                f"💎 Destek: {VIP_KANAL}"
            )
        )
    except Exception as e:
        print(f"❌ Kullaniciya bildirim gonderilemedi: {e}")


def admin_davet_siralama(update, context):
    user_id = update.message.from_user.id

    if not admin_mi(user_id):
        update.message.reply_text("🚫 Yetkiniz yok!")
        return

    davetler = veritabani_yukle(DAVET_DOSYA)
    info = veritabani_yukle(INFO_DOSYA)

    if not davetler:
        update.message.reply_text("📭 Heniz davet verisi yok.")
        return

    siralama = sorted(
        davetler.items(),
        key=lambda x: x[1].get("toplam_davet", 0),
        reverse=True
    )[:20]

    mesaj = "🏆 EN COK DAVET EDENLER (Top 20)\n\n"
    for i, (uid, data) in enumerate(siralama, 1):
        davet_sayisi = data.get("toplam_davet", 0)
        isim = info.get(uid, {}).get("first_name", "Bilinmiyor")
        username = info.get(uid, {}).get("username", "Yok")
        mesaj += f"{i}. {isim} (@{username}) - {davet_sayisi} davet\n"

    update.message.reply_text(mesaj)



def api_sorgu(url):
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Connection': 'keep-alive'
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            raw_data = response.read().decode('utf-8', errors='replace')

            if not raw_data or raw_data.strip() == '':
                return {"HATA": "API bos yanit dondurdu"}

            try:
                return json.loads(raw_data)
            except json.JSONDecodeError:
                return {"SONUC": raw_data}

    except urllib.error.HTTPError as e:
        return {"HATA": f"HTTP Hatasi: {e.code} - {e.reason}"}
    except urllib.error.URLError as e:
        return {"HATA": f"URL Hatasi: {str(e.reason)}"}
    except Exception as e:
        return {"HATA": f"Sorgu hatasi: {str(e)}"}


def temizle_deger(val):
    if val is None:
        return "-"
    if val == "None":
        return "-"
    if val == "null":
        return "-"
    if val == "":
        return "-"
    if val == " ":
        return "-"
    return str(val)


def formatli_txt_yaz(data):
    if isinstance(data, str):
        return data

    if isinstance(data, dict):
        if "HATA" in data and len(data) == 1:
            return f"❌ HATA: {data['HATA']}"

        if "SONUC" in data and len(data) == 1:
            return data["SONUC"]

        satirlar = []
        for key, val in data.items():
            if key.lower() in ['success', 'status', 'message', 'count', 'number', 'total']:
                continue

            if isinstance(val, list):
                satirlar.append(f"\n📁 {key}:\n")
                for i, item in enumerate(val, 1):
                    satirlar.append(f"\n📋 KAYIT {i}")
                    satirlar.append("═" * 40)
                    if isinstance(item, dict):
                        for k, v in item.items():
                            satirlar.append(f"  🔹 {k}: {temizle_deger(v)}")
                    else:
                        satirlar.append(f"  🔹 {temizle_deger(item)}")
            elif isinstance(val, dict):
                satirlar.append(f"\n📁 {key}:")
                for k, v in val.items():
                    satirlar.append(f"  🔹 {k}: {temizle_deger(v)}")
            else:
                satirlar.append(f"🔹 {key}: {temizle_deger(val)}")

        return "\n".join(satirlar)

    if isinstance(data, list):
        satirlar = []
        for i, item in enumerate(data, 1):
            satirlar.append(f"\n📋 KAYIT {i}")
            satirlar.append("═" * 40)
            if isinstance(item, dict):
                for k, v in item.items():
                    satirlar.append(f"🔹 {k}: {temizle_deger(v)}")
            else:
                satirlar.append(f"🔹 {temizle_deger(item)}")
        return "\n".join(satirlar)

    return str(data)


# işlevler (ban...)

def start(update, context):
    user_id = update.message.from_user.id

    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    if context.args:
        referans_sahibi = context.args[0]
        if referans_sahibi != str(user_id):
            try:
                davet_eden_id = int(referans_sahibi)
                davet_edilen_id = user_id
                davet_edilen_username = update.message.from_user.username or "Yok"
                davet_edilen_first_name = update.message.from_user.first_name or "Isimsiz"

                davet_kaydet(davet_eden_id, davet_edilen_id, davet_edilen_username, davet_edilen_first_name)

                referans_kullanici = kullanici_getir(veritabani, davet_eden_id)
                referans_kullanici["sorgu_hakki"] += 5
                referans_kullanici["referans_sayisi"] += 1
                veritabani_kaydet(KULLANICI_DOSYA, veritabani)

                yeni_kullanici = kullanici_getir(veritabani, user_id)
                yeni_kullanici["sorgu_hakki"] += 5
                veritabani_kaydet(KULLANICI_DOSYA, veritabani)
            except Exception as e:
                print(f"❌ Referans hatasi: {e}")

    kullanici = kullanici_getir(veritabani, user_id)
    if kullanici.get("ban", False):
        update.message.reply_text("🚫 Hesabiniz banlanmis! VIP kanali ile iletisime gecin.")
        return

    eksik_kanallar = kanal_kontrol(update, context, user_id)
    if eksik_kanallar:
        kanal_mesaji_gonder(update)
        return

    hosgeldin_menusu_gonder(update, context, veritabani)


def sorgu_yap(update, context, sorgu_tipi, api_url_template, param_sayisi):
    user_id = update.message.from_user.id

    veritabani = veritabani_yukle(KULLANICI_DOSYA)

    kullanici = kullanici_getir(veritabani, user_id)
    if kullanici.get("ban", False):
        update.message.reply_text("🚫 Hesabiniz banlanmis!")
        return

    eksik_kanallar = kanal_kontrol(update, context, user_id)
    if eksik_kanallar:
        kanal_mesaji_gonder(update)
        return

    vip_kontrol(veritabani, user_id)
    kullanici = kullanici_getir(veritabani, user_id)

    kalan_hak = sorgu_hakki_kontrol(veritabani, user_id)
    if kalan_hak <= 0 and not kullanici.get("vip", False):
        update.message.reply_text(
            "⚠️ Gunluk sorgu hakkin bitti!\n\n"
            f"🔄 Yarin 00:00'da {GUNLUK_SORGU_HAKKI} hak yenilenecek.\n\n"
            f"💎 VIP uyelik icin: {VIP_KANAL}\n"
            f"🔗 Referans kazanmak icin /start yaz."
        )
        return

    text = update.message.text.strip()
    args = text.split()[1:]

    if len(args) < param_sayisi:
        update.message.reply_text("❌ Eksik parametre! /start yazarak komutlari gor.")
        return

    try:
        if sorgu_tipi == "ADSOYAD":
            ad = urllib.parse.quote(args[0])
            soyad = urllib.parse.quote(args[1])
            api_url = api_url_template.format(ad, soyad)
            yapilan_islem = f"Ad: {args[0]}, Soyad: {args[1]}"
            sonuc_baslik = f"📋 AD SOYAD SORGUSU - {args[0]} {args[1]}"
        else:
            api_url = api_url_template.format(args[0])
            yapilan_islem = f"TC: {args[0]}"
            sonuc_baslik = f"📋 {sorgu_tipi} SORGUSU - TC: {args[0]}"
    except Exception as e:
        update.message.reply_text(f"❌ URL olusturma hatasi: {e}")
        return

    user = update.message.from_user
    username = user.username or "Bilinmiyor"

    if not kullanici.get("vip", False):
        if not sorgu_hakki_dusur(veritabani, user_id):
            update.message.reply_text("⚠️ Sorgu hakkin bitti!")
            return

    info_sorgu_artir(user_id)

    log_gonder(username, user_id, sorgu_tipi, yapilan_islem)

    yeni_hak = sorgu_hakki_kontrol(veritabani, user_id)
    update.message.reply_text(f"🔍 {sorgu_tipi} sorgusu yapiliyor... (💾 Kalan hak: {yeni_hak})")

    data = api_sorgu(api_url)
    duzgun_sonuc = formatli_txt_yaz(data)

    zaman_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

    txt_icerik = (
        f"{'═'*50}\n"
        f"📋 {sonuc_baslik}\n"
        f"⏰ Zaman: {zaman_str}\n"
        f"{'═'*50}\n"
        f"{duzgun_sonuc}"
    )

    gonderildi = txt_dosya_gonder(update, context, txt_icerik, "sonuc.txt")

    if not gonderildi:
        kisa_sonuc = duzgun_sonuc[:3000]
        if len(duzgun_sonuc) > 3000:
            kisa_sonuc += "\n\n... (devami var)"
        update.message.reply_text(f"{sonuc_baslik}\n\n{kisa_sonuc}")


def adres(update, context):
    sorgu_yap(update, context, "ADRES", API_ADRES, 1)

def tcgsm(update, context):
    sorgu_yap(update, context, "GSM", API_GSM, 1)

def sulale(update, context):
    sorgu_yap(update, context, "SULALE", API_SULALE, 1)

def adsoyad(update, context):
    sorgu_yap(update, context, "ADSOYAD", API_ADSOYAD, 2)

def tcpro(update, context):
    sorgu_yap(update, context, "TCPRO", API_TCPRO, 1)

def isyeri(update, context):
    sorgu_yap(update, context, "ISYERI", API_ISYERI, 1)

def okul(update, context):
    sorgu_yap(update, context, "OKUL", API_OKUL, 1)


def hatali_komut(update, context):
    update.message.reply_text("❌ Hatali komut veya eksik parametre!\n\n➡️ /start yazarak komutlari gor.")


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("adres", adres))
    dp.add_handler(CommandHandler("tcgsm", tcgsm))
    dp.add_handler(CommandHandler("sulale", sulale))
    dp.add_handler(CommandHandler("adsoyad", adsoyad))
    dp.add_handler(CommandHandler("tcpro", tcpro))
    dp.add_handler(CommandHandler("isyeri", isyeri))
    dp.add_handler(CommandHandler("okul", okul))

    dp.add_handler(CommandHandler("davetlerim", davetlerim))
    dp.add_handler(CommandHandler("vipodul", vipodul))

    dp.add_handler(CommandHandler("admin", admin_panel))
    dp.add_handler(CommandHandler("ban", admin_ban))
    dp.add_handler(CommandHandler("unban", admin_unban))
    dp.add_handler(CommandHandler("hak", admin_hak))
    dp.add_handler(CommandHandler("all", admin_all))
    dp.add_handler(CommandHandler("vip", admin_vip))
    dp.add_handler(CommandHandler("normal", admin_normal))
    dp.add_handler(CommandHandler("stats", admin_stats))
    dp.add_handler(CommandHandler("list", admin_list))
    dp.add_handler(CommandHandler("info", admin_info))
    dp.add_handler(CommandHandler("viptalepler", admin_vip_talepler))
    dp.add_handler(CommandHandler("viponayla", admin_vip_onayla))
    dp.add_handler(CommandHandler("vipreddet", admin_vip_reddet))
    dp.add_handler(CommandHandler("davetsiralama", admin_davet_siralama))

    dp.add_handler(CallbackQueryHandler(komutlar_callback, pattern="komutlar"))
    dp.add_handler(CallbackQueryHandler(nasil_kullanilir_callback, pattern="nasil_kullanilir"))
    dp.add_handler(CallbackQueryHandler(sorgu_hakki_callback, pattern="sorgu_hakki"))
    dp.add_handler(CallbackQueryHandler(referans_link_callback, pattern="referans_link"))
    dp.add_handler(CallbackQueryHandler(invite_gifts_callback, pattern="invite_gifts"))
    dp.add_handler(CallbackQueryHandler(davetlerim_detay_callback, pattern="davetlerim_detay"))
    dp.add_handler(CallbackQueryHandler(geri_don_callback, pattern="geri_don"))

    dp.add_handler(MessageHandler(Filters.command, hatali_komut))

    print("💎 LIBRA Ucretsiz Sorgu Botu calisiyor...")
    print("🌐 Flask web sunucusu: http://0.0.0.0:8080")
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
