import time
import datetime
import sqlite3
import os
import json
import asyncio
import requests
import re
import pytz

try :
    import telegram
    from telegram.ext import JobQueue ,Updater, CommandHandler, Application, MessageHandler, filters
except :
    for x in ["python-telegram-bot", "pip install python-telegram-bot[job-queue]"] :
        os.system(f"pip install {x}")
    import telegram
    from telegram.ext import JobQueue, Updater, CommandHandler, Application, MessageHandler, filters

TOKEN = '6252173085:AAEzBU2ocBmvqYwNAs6LoY5V5LmNG7Fggcc'
bot = telegram.Bot(token=TOKEN)
url = "http://{}:5000".format("192.168.1.43")

print_json = lambda a : print(json.dumps(a, indent = 4))

# Fungsi untuk membuat tabel di database
def create_table():
    conn = sqlite3.connect('member.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS member
                 (MacAddress integer, Name text, joined_date text, status integer)''')
    conn.commit()
    conn.close()

# Fungsi untuk menambahkan anggota ke database
def add_member(MacAddress, Name, joined_date, status):
    conn = sqlite3.connect('member.db')
    c = conn.cursor()
    c.execute("INSERT INTO member (MacAddress, Name, joined_date, status) SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM member WHERE MacAddress = ?)", (MacAddress, Name, joined_date, status, MacAddress))
    add_device = requests.get("{}/unban?name={}".format(url, Name, MacAddress))
    conn.commit()
    conn.close()

# Fungsi untuk menghapus anggota dari database
def delete_member(Name, MacAddress):
    conn = sqlite3.connect('member.db')
    c = conn.cursor()
    c.execute("DELETE FROM member WHERE MacAddress=?", (MacAddress,))
    conn.commit()
    conn.close()
    ban_device = requests.get("{}/ban?name={}&mac={}".format(url, Name, MacAddress))
    return ban_device

def getLocalTime() :
    jakartaZone = pytz.timezone("Asia/Jakarta")
    currentTimeInJakarta = datetime.datetime.now(jakartaZone).strftime("%Y-%m-%d %H:%M:%S")
    return currentTimeInJakarta

# Fungsi untuk memeriksa masa aktif anggota
async def check_member(chat_id):
    conn = sqlite3.connect('member.db')
    c = conn.cursor()
    current_time = getLocalTime().timestamp()

    for row in c.execute('SELECT * FROM member'):
        MacAddress = row[0]
        Name = row[1]
        joined_data = row[2]
        joined_time = datetime.datetime.strptime(joined_date, '%Y-%m-%d %H:%M:%S').timestamp()
        if (current_time - joined_time) > (60 * 60 * 24 * 30): # 30 hari
            delete_member(MacAddress, Name)
            pass

    conn.close()

# Fungsi untuk menangani perintah '/add' dari pengguna
async def add(update, context) :

    def check_format(data) :

        if len(data) != 2 and not "".join(data).strip() :
            return (False, "")

        name = data[0]
        maskMacId = r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"
        MacId = re.search(maskMacId,data[1])

        if MacId :
            return (True, "Check Passed")

        return (False, "Format Mac atau Nama Tidak Benar")

    validation = check_format(context.args)

    if not validation[0] :
        await update.message.reply_text("""Format tambah member tidak benar!
Keterangan : {}""".format(validation[1]))

    name = context.args[0]
    MacAddress = context.args[1]
    joined_date = getLocalTime()
    status = 1

    add_member(MacAddress, name, joined_date, status)
    await update.message.reply_text("Anggota berhasil ditambahkan!")

# Fungsi untuk menangani perintah '/ban' dari pengguna
async def ban(update, context) :

    def check_format(data) :

        if len(data) != 2 or not "".join(data).strip() :
            return (False, "")

        name = data[0]
        maskMacId = r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"
        MacId = re.search(maskMacId,data[1])

        if MacId :
            return (True, "Check Passed")

        return (False, "Format Mac atau Nama Tidak Benar")

    validation = check_format(context.args)

    if not validation[0] :
        await update.message.reply_text("""Format banned member tidak benar!
Keterangan : {}""".format(validation[1]))
        return

    name = context.args[0]
    mac = context.args[1]
    ban_device = delete_member(name, mac)

    if ban_device.status_code in range(400,600) :
        await update.message.reply_text("<ERROR> Member gagal di Banned! </ERROR>")
        return

    await update.message.reply_text("Member berhasil di Banned!")

async def unban(update, context) :

    def check_format(data) :
        if len(data) != 2 or not "".join(data).strip() :
            return (False, "")

        unban_type = True if data[0] in ["name", "mac"] else False
        value = data[1].strip()

        if unban_type and value :
            return (True, "Check Passed")

        return (False, "Format type atau value Tidak Benar")

    validation = check_format(context.args)

    if not validation[0] :
        await update.message.reply_text("""Format unbanned member tidak benar!
Keterangan : {}""".format(validation[1]))
        return

    unban_type = context.args[0]
    value = context.args[1]

    req_device = requests.get("{}/unban?{}={}".format(url, unban_type, value))

    if req_device.status_code in range(400,600) :
        await update.message.reply_text("<ERROR> Member gagal di un-Banned! </ERROR>")
        return

    data_device = req_device.json()
    name = data_device.get("Name")
    MacAddress = data_device.get("MacAddress")
    joined_date = getLocalTime()
    status = 1

    add_member(MacAddress, name, joined_date, status)

    await update.message.reply_text("Member berhasil di un-Banned!")



# Fungsi utama
def main():
    create_table()
    app = Application.builder().token(TOKEN).build()
    # print(app.job_queue, type(app.job_queue))
    # app.job_queue().run_repeating(hola, interval = 5)
    # JobQueue().run_once(callback = hola, interval = 10)
    app.add_handler(CommandHandler('add', add))
    app.add_handler(CommandHandler('ban', ban))
    app.add_handler(CommandHandler('unban', unban))
    # app.add_handler(CommandHandler('kick', kickByInterval, block = False))
    # app.add_handler(MessageHandler(filters.TEXT, handle_msg))
    app.run_polling()

main()
