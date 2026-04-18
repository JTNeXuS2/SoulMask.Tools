import json
import unicodedata
import datetime
import asyncio
import os
import requests
import time
import re
import subprocess
import aiohttp
from collections import deque
import configparser

# Конфигурация
def read_cfg():
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
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
        config.optionxform = str
    
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
            
            id_list_raw = config.get('admins', 'id_list').strip().split('\n')
            id_list = [line.strip() for line in id_list_raw if line.strip()]
            
            log_files = []
            log_files_dict = {}
            for server_name, log_path in config.items('logs'):
                log_files.append(log_path)
                log_files_dict[log_path] = server_name
                
        except KeyError as e:
            print(f"Error: missing section or key in config file: {e}")

# Инициализация
webhook_url = None
chat_webhook_url = None
DISCORD_WEBHOOK_USERNAME = None
id_list = []
log_files = []
log_files_dict = {}

update_settings()

# Настройки для Shard
MAX_MESSAGES_PER_BATCH = 10  # Максимум сообщений в одном запросе
BATCH_DELAY = 1.0  # Задержка между пакетами (сек)
MAX_RETRIES = 3

# Проверка файлов
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

async def send_discord_webhook_direct(webhook_url, message):
    """Прямая отправка сообщения без буфера"""
    data = {'content': message, 'username': DISCORD_WEBHOOK_USERNAME}
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(MAX_RETRIES):
            try:
                async with session.post(webhook_url, json=data) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = float(response.headers.get('Retry-After', 5))
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Rate limit, waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 204:
                        return True  # Успешно отправлено
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] HTTP {response.status}")
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(1)
                        continue
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                continue
        
        return False

async def send_batch_messages(messages_batch):
    """Отправка пакета сообщений через один Webhook"""
    if not messages_batch:
        return
    
    # Для Webhook можно отправлять несколько сообщений через запятые или использовать вложенность
    # Но проще отправлять по одному, но с умным управлением задержками
    
    for webhook_url, message in messages_batch:
        await send_discord_webhook_direct(webhook_url, message)
        await asyncio.sleep(0.2)  # Минимальная задержка между сообщениями

# Очередь сообщений для пакетной обработки
message_queue = asyncio.Queue()
last_send_time = 0

async def send_discord_webhook(webhook_url, message):
    """Добавляет сообщение в очередь для пакетной отправки"""
    await message_queue.put((webhook_url, message))

async def process_queue():
    """Обрабатывает очередь сообщений с умной пакетизацией"""
    batch = []
    
    while True:
        try:
            # Пытаемся получить сообщение с таймаутом
            webhook_url, message = await asyncio.wait_for(message_queue.get(), timeout=BATCH_DELAY)
            batch.append((webhook_url, message))
            
            # Если набрали достаточно сообщений или очередь пуста - отправляем
            if len(batch) >= MAX_MESSAGES_PER_BATCH or message_queue.empty():
                await send_batch_messages(batch)
                batch = []
                
        except asyncio.TimeoutError:
            # Таймаут - отправляем то, что есть
            if batch:
                await send_batch_messages(batch)
                batch = []
        except Exception as e:
            print(f"Error processing queue: {e}")
            await asyncio.sleep(1)

async def read_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        return []

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
        for leave_line in log_lines:
            if "logStoreGamemode: player ready." in leave_line:
                match = re.search(r"\[([^\]]+)\]\[(\d+)\]logStoreGamemode: player ready\. Addr:([^,]+),\s*Netuid:([^,]+),\s*Name:(.+)", leave_line)
                if match:
                    netuid = match.group(4).strip()
                    name = match.group(5).strip()
                    ready_players[netuid] = name
        
        for line in new_lines:
            # Log админов
            if any(id_ in line for id_ in id_list):
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
                    channel = match.group(1).strip()
                    clan = match.group(2).strip()
                    name = match.group(3).strip()
                    id_ = match.group(4)
                    message = match.group(5).strip()

                    display_clan = f"[{clan}] " if clan else ""
                    await send_discord_webhook(chat_webhook_url, f"[{channel}] **{display_clan}{name}**: {message}")
            
            # Join
            if "logStoreGamemode: player ready." in line:
                if (match := re.search(r"\[([^\]]+)\]\[(\d+)\]logStoreGamemode: player ready\. Addr:([^,]+),\s*Netuid:([^,]+),\s*Name:(.+)", line)):
                    addr = match.group(3).strip()
                    netuid = match.group(4).strip()
                    name = match.group(5).strip()
                    await send_discord_webhook(chat_webhook_url, f":tada: **{name}** Join the world! :tada:")

            # Leave
            if "logStoreGamemode: Display: player leave world." in line:
                match = re.search(r"\[([^\]]+)\]\[([^]]+)\]logStoreGamemode: Display: player leave world\. (.+)", line)
                if match:
                    steam_id = match.group(3).strip()
                    if steam_id in ready_players:
                        name = ready_players[steam_id]
                        await send_discord_webhook(chat_webhook_url, f":arrow_down: **{name}** Left the world! :arrow_down:")
    
    last_lines[log_filename] = len(log_lines)

async def main():
    # Запускаем обработчик очереди вместо буфера
    queue_task = asyncio.create_task(process_queue())
    
    while True:
        tasks = [process_log_file(log_file) for log_file in log_files]
        await asyncio.gather(*tasks)
        await asyncio.sleep(5)  # Проверка каждые 5 секунд

if __name__ == "__main__":
    asyncio.run(main())
    
