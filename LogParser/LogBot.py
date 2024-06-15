import disnake
from disnake.ext import commands
from disnake import Intents
import json
import configparser
import unicodedata
import datetime

import asyncio
import os
# Need "pip install requests"
import requests
import time
import re
import subprocess

#from pytonik_ip_vpn_checker.ip import ip
#Set discord webhook URL
webhook_url = "https://discord.com/api/webhooks/1246941454870249636/xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

#Set admins SteamIDs, add custom param to find
id_list = [
            'logStoreGamemode: player ready.',
            'logStoreGamemode: Display: player leave world.',
            'ASGGameModeLobby',
            'remote console, exec:'
            ]

#Set full path to servers logs
log_files = [
    'C:/wgsm/servers/1/serverfiles/WS/Saved/Logs/WS.log'
]

#Set match the server name and log file
log_files_dict = {
    'C:/wgsm/servers/1/serverfiles/WS/Saved/Logs/WS.log': '**PVE-K**'
}

#Nothing change more

missing_files = []
for log_file in log_files:
    if not os.path.exists(log_file):
        missing_files.append(log_file)

if missing_files:
    missing_files_str = "\n".join(missing_files)
    print(f"The following files are missing:")
    print(missing_files_str)
else:
    print("All log files are present.")

async def read_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        #print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] File not found: {file_path}")
        return []

async def send_discord_webhook(webhook_url, message):
    data = {'content': message}
    try:
        requests.post(webhook_url, json=data)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error sending Discord webhook: {e}")

last_lines = {os.path.basename(log_file): None for log_file in log_files}
async def process_log_file(log_file):
    log_lines = await read_log_file(log_file)
    log_filename = os.path.basename(log_file)
    
    if log_filename in last_lines:
        if last_lines[log_filename] is not None:
            new_lines = log_lines[last_lines[log_filename] or 0:]
            for line in new_lines:
                if any(id in line for id in id_list):
                    if re.match(r'\[\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3}\]\[\s*\d+\]', line):
                        server_name = log_files_dict.get(log_file, "Unknown Server")

                        print(f"{server_name} ```({log_filename}): {line}```\n")
                        await send_discord_webhook(webhook_url, f"{server_name}\n```({log_filename}): {line}```")
        last_lines[log_filename] = len(log_lines)
    else:
        print(f"Key '{log_filename}' not found in last_lines dictionary")


async def main():
    while True:
        tasks = [process_log_file(log_file) for log_file in log_files]
        await asyncio.gather(*tasks)
        await asyncio.sleep(10)  # Проверка каждые 10 секунд
        #print('CheckLogs')

asyncio.run(main())
