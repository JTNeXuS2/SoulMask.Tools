import re
import subprocess
from datetime import datetime, timedelta
import asyncio
import os
# pip install sqlite3
import sqlite3

log_file = 'WS.log'

bans_db = 'bans.db'
# trigger threshold, how many times an IP address must be found in (NotifyAcceptingConnection accepted) before it is included in the ban list
sensitive = 150
# period scan log in sec
cooldown = 5
# ban_time in min
ban_time = 60

async def unban(conn):
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Получаем адреса, которые будут разблокированы
    cursor.execute("SELECT address FROM ip_address WHERE time <= ? OR white = 1", (current_datetime,))
    addresses_to_unban = cursor.fetchall()
    # Разблокировка адресов
    for row in addresses_to_unban:
        address = row[0]
        print(f"Unban {address}")
        subprocess.run(f'cmd.exe /c netsh advfirewall firewall delete rule name="Block Specific IP" remoteip={address}', shell=True)
    cursor.execute("DELETE FROM ip_address WHERE time <= ? AND (white IS NULL OR white <> 1)", (current_datetime,))
    conn.commit()


async def add_and_block_ip(ip, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ip_address WHERE address=?", (ip,))
    white = cursor.fetchone()
    if not white:
        current_datetime = (datetime.now() + timedelta(minutes=ban_time)).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Ban {current_datetime} = {ip}")

        cursor = conn.cursor()
        cursor.execute("INSERT INTO ip_address (time, address) VALUES (?, ?)", (current_datetime, ip))
        conn.commit()

        # Execute the command to block the IP address using subprocess if needed
        subprocess.run(f'cmd.exe /c netsh advfirewall firewall add rule name="Block Specific IP" dir=in action=block remoteip={ip}', shell=True)

async def process_log_file(conn):

    cursor = conn.cursor()

    with open(log_file, 'r', encoding='utf-8') as file:
        ip_counts = {}
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

        for line in file:
            match = ip_pattern.search(line)
            if match:
                ip = match.group(0)
                ip_counts[ip] = ip_counts.get(ip, 0) + 1

        for ip, count in ip_counts.items():
            if count > sensitive:
                cursor.execute("SELECT * FROM ip_address WHERE address=?", (ip,))
                existing_ban = cursor.fetchone()
                if not existing_ban:
                    cursor.execute("SELECT * FROM ip_address WHERE address=? AND white=?", (ip, 1))
                    white_list = cursor.fetchone()
                    if not white_list:
                        await add_and_block_ip(ip, conn)

    conn.commit()

async def tread1(conn):
    while True:
        try:
            await unban(conn)
        except Exception as e:
            print(f"An error: {e}")
        await asyncio.sleep(60)

async def tread2(conn):
    while True:
        try:
            await process_log_file(conn)  # Execute the log file processing
        except Exception as e:
            print(f"An error: {e}")
        await asyncio.sleep(cooldown)

async def main():
    conn = sqlite3.connect(bans_db, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ip_address
                      (time TEXT, address TEXT UNIQUE, white TEXT)''')
    conn.commit()

    if os.path.exists(log_file):
        print('Working...')
        try:
            await asyncio.gather(tread1(conn), tread2(conn))
        finally:
            conn.close()
    else:
        print(f'{log_file} NOT FOUND')

asyncio.run(main())
