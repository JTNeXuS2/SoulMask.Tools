import json
import unicodedata
import datetime
import asyncio
import os
# Need "pip install requests"
import requests
import time
import re
import subprocess

import aiohttp
from collections import deque

import configparser

def read_cfg():
    config = configparser.ConfigParser(interpolation=None)
    # Сохраняем оригинальный регистр ключей и пробелы
    config.optionxform = str  # Отключает приведение к нижнему регистру
    try:
        with open('config.ini', 'r', encoding='utf-8') as file:
            config.read_file(file)
    except FileNotFoundError:
        print("Error: Config.ini not found.")
        return None
    return config

async def write_cfg(section, key, value):
    config = read_cfg()
    if config is None:
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str  # Сохраняем регистр при записи
    
    if section not in config:
        config[section] = {}
    config[section][key] = str(value)

    with open('config.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)

def update_settings():
    global webhook_url, chat_webhook_url, DISCORD_WEBHOOK_USERNAME, id_list, log_files, log_files_dict
    
    config = read_cfg()
    if config:
        try:
            webhook_url = config['botconfig']['webhook_url']
            chat_webhook_url = config['botconfig']['chat_webhook_url']
            DISCORD_WEBHOOK_USERNAME = config['botconfig']['DISCORD_WEBHOOK_USERNAME']
            
            # Чтение id_list (каждая строка отдельно)
            id_list_raw = config.get('admins', 'id_list').strip().split('\n')
            id_list = [line.strip() for line in id_list_raw if line.strip()]
            
            # Чтение log_files и log_files_dict из секции logs
            log_files = []
            log_files_dict = {}
            # Используем items() для сохранения оригинальных ключей с пробелами
            for server_name, log_path in config.items('logs'):
                log_files.append(log_path)
                log_files_dict[log_path] = server_name  # server_name сохраняет пробелы
                
        except KeyError as e:
            print(f"Error: missing section or key in config file: {e}")

# Инициализация переменных с значениями по умолчанию
webhook_url = None
chat_webhook_url = None
DISCORD_WEBHOOK_USERNAME = None
id_list = []
log_files = []
log_files_dict = {}

# Загрузка настроек
update_settings()

#pip install ipwhois
#from ipwhois import IPWhois

#from pytonik_ip_vpn_checker.ip import ip
#Set discord webhook URL

# Буфер для сообщений (deque для FIFO)
message_buffer = deque()
# Настройки
WEBHOOK_RATE_LIMIT_DELAY = 0.2  # Задержка между отправками (сек, чтобы не превышать лимит ~5/сек)
MAX_RETRIES = 3  # Максимум повторных попыток при ошибке

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
'''
async def send_discord_webhook(webhook_url, message):
    data = {'content': message}
    try:
        requests.post(webhook_url, json=data)
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error sending Discord webhook: {e}")
'''
async def send_discord_webhook(webhook_url, message):
    """Добавляет сообщение в буфер для асинхронной отправки."""
    message_buffer.append((webhook_url, message))
    #print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Message added to buffer: {message[:50]}...")

async def process_buffer():
    """Асинхронно обрабатывает буфер и отправляет сообщения с учётом rate limits."""
    async with aiohttp.ClientSession() as session:
        while True:
            if message_buffer:
                webhook_url, message = message_buffer.popleft()
                await send_with_retry(session, webhook_url, message)
            await asyncio.sleep(WEBHOOK_RATE_LIMIT_DELAY)

async def send_with_retry(session, webhook_url, message, retry_count=0):
    """Отправляет сообщение с повторными попытками при ошибке."""
    data = {'content': message}
    data['username'] = DISCORD_WEBHOOK_USERNAME 
    try:
        async with session.post(webhook_url, json=data) as response:
            if response.status == 429:  # Rate limit exceeded
                retry_after = float(response.headers.get('Retry-After', 5))  # Время ожидания из заголовка
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Rate limit hit, waiting {retry_after}s...")
                await asyncio.sleep(retry_after)
                if retry_count < MAX_RETRIES:
                    await send_with_retry(session, webhook_url, message, retry_count + 1)
            elif response.status != 204:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP error {response.status}: {await response.text()}")
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(1)  # Ждать 1 сек перед повтором
                    await send_with_retry(session, webhook_url, message, retry_count + 1)
            else:
                #print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Message sent successfully")
                pass
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error sending Discord webhook: {e}")
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(1)
            await send_with_retry(session, webhook_url, message, retry_count + 1)
            
last_lines = {os.path.basename(log_file): None for log_file in log_files}
async def process_log_file(log_file):
    log_lines = await read_log_file(log_file)
    log_filename = os.path.basename(log_file)

    if log_filename not in last_lines:
        print(f"Key '{log_filename}' not found in last_lines dictionary")
        return

    if last_lines[log_filename] is not None:
        new_lines = log_lines[last_lines[log_filename] or 0:]
        
        ready_players = {}
        for leave_line in log_lines:  # Перебираем все строки, чтобы учесть старые ready
            if "logStoreGamemode: player ready." in leave_line:
                match = re.search(r"\[([^\]]+)\]\[(\d+)\]logStoreGamemode: player ready\. Addr:([^,]+),\s*Netuid:([^,]+),\s*Name:(.+)", leave_line)
                if match:
                    netuid = match.group(4).strip()
                    name = match.group(5).strip()
                    ready_players[netuid] = name
        
        for line in new_lines:
            # Log
            if any(id in line for id in id_list):
                if re.match(r'\[\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3}\]\[\s*\d+\]', line):
                    server_name = log_files_dict.get(log_file, "Unknown Server")

                    print(f"{server_name} ```({log_filename}): {line}```\n")
                    await send_discord_webhook(webhook_url, f"{server_name}\n```({log_filename}): {line}```")

            # Chat
            if "logWorldChat: Display:" in line or "logNearChat: Display:" in line:
                match = re.search(
                    r"log(World|Near)Chat: Display: \[\s*([^,\]]*)\s*,\s*([^()]+)\s*\(\s*(\d+)\s*\)\s*\]\s*(.+)",
                    line
                )
                if match:
                    channel = match.group(1).strip()  # "World" или "Near"
                    clan = match.group(2).strip()
                    name = match.group(3).strip()
                    id_ = match.group(4)
                    message = match.group(5).strip()

                    display_clan = f"[{clan}] " if clan else ""
                    await send_discord_webhook(chat_webhook_url,f"[{channel}] **{display_clan}{name}**: {message}")
            # join
            if "logStoreGamemode: player ready." in line:
                if (match := re.search(r"\[([^\]]+)\]\[(\d+)\]logStoreGamemode: player ready\. Addr:([^,]+),\s*Netuid:([^,]+),\s*Name:(.+)", line)):
                    addr = match.group(3).strip()
                    netuid = match.group(4).strip()
                    name = match.group(5).strip()
                    # Отправляем уведомление в Discord
                    await send_discord_webhook(chat_webhook_url, f":tada: **{name}** Join the world! :tada:")

            # Leave
            if "logStoreGamemode: Display: player leave world." in line:
                match = re.search(r"\[([^\]]+)\]\[([^]]+)\]logStoreGamemode: Display: player leave world\. (.+)", line)
                if match:
                    steam_id = match.group(3).strip()
                    if steam_id in ready_players:
                        name = ready_players[steam_id]
                        await send_discord_webhook(chat_webhook_url, f":arrow_down: **{name}** Left the world! :arrow_down:")
            # Other
    last_lines[log_filename] = len(log_lines)

async def main():
    # Запускаем обработчик буфера в фоне
    buffer_task = asyncio.create_task(process_buffer())
    
    while True:
        tasks = [process_log_file(log_file) for log_file in log_files]
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)  # Проверка каждые 5 секунд
        # print('CheckLogs')  # Раскомментируйте для отладки

if __name__ == "__main__":
    asyncio.run(main())
