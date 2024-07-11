import re
import subprocess
from datetime import datetime, timedelta
import asyncio
import os
import sqlite3

log_file = 'WS.log'

bans_db = 'bans.db'
# trigger threshold, how many times an IP address must be found in (NotifyAcceptingConnection accepted) before it is included in the ban list
sensitive = 150
# period scan log in sec
cooldown = 10
# ban_time in min
ban_time = 60

async def unban(conn):
    cursor = conn.cursor()
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Получаем адреса, которые будут разблокированы
    #cursor.execute("SELECT address FROM ip_address WHERE time <= ?", (current_datetime,))
    cursor.execute("SELECT address FROM ip_address WHERE (time <= ? OR white = 1) AND player_name IS NULL", (current_datetime,))
    addresses_to_unban = cursor.fetchall()
    # Разблокировка адресов
    for row in addresses_to_unban:
        address = row[0]
        print(f"Unban {address}")
        subprocess.run(f'cmd.exe /c netsh advfirewall firewall delete rule name="Block Specific IP" remoteip={address}', shell=True)
        cursor.execute("DELETE FROM ip_address WHERE time <= ? AND (white IS NULL OR white <> 1 OR player_name IS NULL)", (current_datetime,))
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

async def add_ip_name(player_address, player_name, conn):
    #cursor = conn.cursor()
    #cursor.execute("SELECT * FROM ip_address WHERE address=?", (ip,))
    #white = cursor.fetchone()
    #if not white:
    print(f"IP: {player_address}, Name: {player_name}")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO ip_address (player_name, address) VALUES (?, ?)", (player_name, player_address))
    conn.commit()

async def process_log_file(conn):

    cursor = conn.cursor()

    with open(log_file, 'r', encoding='utf-8') as file:
        ip_counts = {}
        #ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')  # All strings
        ip_pattern = re.compile(r'LogNet: NotifyAcceptingConnection accepted from: (\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)')  # strings only prefix
        # Паттерн для извлечения IP-адреса и имени
        name_pattern = r"Addr:(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}),.*Name:(\w+)"

        for line in file:
            match = ip_pattern.search(line)
            if match:
                ip = match.group(1)
                ip_counts[ip] = ip_counts.get(ip, 0) + 1

            matches = re.search(name_pattern, line)
            if matches:
                player_address = matches.group(1)
                player_name = matches.group(2)

                cursor.execute("SELECT * FROM ip_address WHERE address=?", (player_address,))
                existing_ban = cursor.fetchone()
                if not existing_ban:
                    await add_ip_name(player_address, player_name, conn)

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
                      (time TEXT, address TEXT UNIQUE, white TEXT, player_name TEXT)''')
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
