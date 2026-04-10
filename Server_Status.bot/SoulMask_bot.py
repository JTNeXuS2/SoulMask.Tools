#Python 3.8 or higher is required.
#py -3 -m pip install -U disnake
#pip3 install python-a2s
import disnake
from disnake.ext import commands, tasks
from disnake import Intents
import json
import datetime
import a2s
import requests
import configparser
import re
import unicodedata

import aiofiles
import aiohttp

import sys
import asyncio
import telnetlib3  # Вместо telnetlib
import time
import os
import subprocess
from urllib.parse import urlparse, unquote, parse_qs
#cant used
prefix = '/'

#Nothing change more

def read_cfg():
    config = configparser.ConfigParser(interpolation=None)
    try:
        with open('config.ini', 'r', encoding='utf-8') as file:
            config.read_file(file)
    except FileNotFoundError:
        print("Error: Config.ini not found.")
        return None
    return config
async def write_cfg(section, key, value):
    config = read_cfg()
    if f'{section}' not in config:
        config[f'{section}'] = {}
    config[f'{section}'][f'{key}'] = str(f'{value}')

    with open('config.ini', 'w', encoding='utf-8') as configfile:
        config.write(configfile)
def update_settings():
    global token, channel_id, message_id , update_time, bot_name, bot_ava, address, command_prefex, HOST, RCONPORT, PASSWORD, crosschat_id

    config = read_cfg()

    if config:
        try:
            token = config['botconfig']['token']
            channel_id = config['botconfig']['channel_id']
            message_id = config['botconfig']['message_id']
            bot_name = config['botconfig']['bot_name']
            bot_ava = config['botconfig']['bot_ava']
            update_time = config['botconfig']['update_time']
            command_prefex = config['botconfig']['command_prefex'].lower()
            address = (f"{config['botconfig']['ip']}", int(config['botconfig']['query_port']))
            
            HOST = config['botconfig']['HOST']
            RCONPORT = int(config['botconfig']['RCONPORT'])
            PASSWORD = config['botconfig']['PASSWORD']
            crosschat_id = config['botconfig']['crosschat_id']

        except KeyError as e:
            print(f"Error: wrong lines in config file {e}")

token = None
channel_id = None
message_id = None
bot_name = None
bot_ava = None
update_time = 10
address = None
command_prefex = None
update_settings()

#bot idents
intents = disnake.Intents.default()
intents = disnake.Intents().all()
client = commands.Bot(command_prefix=prefix, intents=intents, case_insensitive=True)
bot = commands.Bot(command_prefix=prefix, intents=intents, case_insensitive=True)

async def get_info(address):
    for attempt in range(3):  # максимум 3 попытки
        try:
            info = a2s.info(address)
            players = a2s.players(address)
            rules = a2s.rules(address)
            return info, players, rules
        except Exception as e:
            if attempt < 2:  # если не последняя попытка
                await asyncio.sleep(10)  # ждём 10 секунд
            else:  # последняя попытка тоже не удалась
                #print(f"An error occurred while getting server info: {e}")
                channel = await bot.fetch_channel(channel_id)
                message = await channel.fetch_message(message_id)
                embed = disnake.Embed(
                    title=f"**{address[0]}:{address[1]}**",
                    colour=disnake.Colour.red(),
                    description=f"offline or cannot answer",
                )
                await message.edit(content=f'Last update: {datetime.datetime.now().strftime("%H:%M")}', embed=embed)

def normalize_string(string):
    return unicodedata.normalize('NFKD', string).encode('utf-8', 'ignore').decode("utf-8")

async def send_annonce(message):
    try:
        message = normalize_string(message)
        command = f"say {message}"
        reply = send_rcon_command(HOST, RCONPORT, PASSWORD, command, raise_errors=True)
        #print("RCON reply:", reply)
    except Exception as e:
        #print(f"Error send_annonce: {e}")
        pass

def send_rcon_command(host, port, rcon_password, command, raise_errors=False, num_retries=3, timeout=4):
    from valve.rcon import RCON, RCONMessageError, RCONAuthenticationError, RCONCommunicationError, RCONMessage, RCONTimeoutError
    import socket
    def strip_rcon_log(response):
        print(response)

    try:
        port = int(port)
    except ValueError:
        #print("Port Error")
        return "Port connection Error"
 
    attempts = 0
    while attempts < num_retries:
        attempts += 1
        try:
            with RCON((host, port), rcon_password, timeout=timeout) as rcon:
                RCONMessage.ENCODING = "utf-8"
                response = rcon(command)
                return strip_rcon_log(response)
        except KeyError:
            # There seems to be a bug in python-vavle where a wrong password
            # trigger a KeyError at line 203 of valve/source/rcon.py,
            # so this is a work around for that.
            raise RconError('Incorrect rcon password')
 
        except (socket.error, socket.timeout,
                RCONMessageError, RCONAuthenticationError) as e:
            if attempts >= num_retries:
                if raise_errors:
                    raise RconError(str(e))
                else:
                    response = "connection error"
                    return strip_rcon_log(response)
        print("repeat send")

# AUTO ANNONCE
import random
def gettime(format):
    return datetime.datetime.now().strftime(format)
current_index = 0
useonce = None
annonce_time = 600
annonce_file = 'annonces.txt'
if not os.path.exists(annonce_file):
    with open(annonce_file, 'w', encoding='utf-8') as f:
        f.write('')

async def auto_annonces(current_index):
    global useonce
    annonces_list = {}
    with open(annonce_file, 'r', encoding='utf-8') as f:
        for index, line in enumerate(f):
            annonces_list[index] = line.strip()
    if not useonce:
        if annonces_list:  # Проверяем, что annonces_list не пустой
            current_index = random.randint(0, len(annonces_list) - 1)
            useonce = 1
        pass
    if annonces_list:
        text = annonces_list.get(current_index, '')
        #print(f'{gettime("[%H:%M:%S-%d.%m.%Y]")} Annonsing: {text}')
        await send_annonce(text)
        current_index += 1
    if current_index > len(annonces_list) - 1:
        current_index = 0
    return current_index

@tasks.loop(seconds=int(annonce_time))
async def annonces():
    global current_index
    try:
        current_index = await auto_annonces(current_index)
    except Exception as e:
        pass
        #print(f'Error annonces:current_index = {current_index} Error:{e}')

@tasks.loop(seconds=10)  # Запуск каждые 10 секунд
async def read_log():
    pass

@tasks.loop(seconds=int(update_time))
async def update_status():
    try:
        info, players, rules = await get_info(address)
    except Exception as e:
        print(f'Failed connect {address} to get server info: {e}')
        await bot.change_presence(
            status=disnake.Status.online,
            activity=disnake.Game(name="Online: ❌ Not answered")
        )
        return

    # Обновление статуса бота
    if info and hasattr(info, 'max_players'):
        player_count = len(players) if players else 0
        activity = disnake.Game(name=f"Online: {player_count}/{info.max_players}")
        await bot.change_presence(status=disnake.Status.online, activity=activity)

    # Обновление имени и аватара бота (если изменились)
    try:
        if bot.user.name != bot_name:
            print(f"u-{bot.user.name} b-{bot_name}")
            await bot.user.edit(username=bot_name)
        
            # Проверяем нужно ли обновлять аватар
            current_avatar = bot.user.avatar.url if bot.user.avatar else None
            if current_avatar != bot_ava:
                async with aiohttp.ClientSession() as session:
                    async with session.get(bot_ava) as response:
                        if response.status == 200:
                            data = await response.read()
                            await bot.user.edit(avatar=data)
    except Exception as e:
        print(f'Failed to update bot profile: {e}')

    # Обновление сообщения в канале
    if info:
        try:
            await update_channel_message(info, rules)
        except Exception as e:
            print(f'Failed to update discord channel message: {e}')
    else:
        print('Cannot connect to server, check IP and query port or server offline')

async def update_channel_message(info, rules):
    """Отдельная функция для обновления сообщения в канале"""
    update_settings()
    
    message = (
        f":earth_africa: Direct Link: **{address[0]}:{info.port}**\n"
        f":link: Invite: **{rules.get('SU_s', 'N/A')}**\n"
        f":map: Map: **{info.map_name}**\n"
        f":green_circle: Online: **{getattr(info, 'player_count', 0)}/{info.max_players}**\n"
        f":asterisk: Pass: **{info.password_protected}**\n"
        f":newspaper: Ver: **{rules.get('NO_s', 'N/A')}**\n"
    )
    
    embed = disnake.Embed(
        title=f"**{info.server_name}**",
        colour=disnake.Colour.green(),
        description=message
    )
    
    channel = await bot.fetch_channel(channel_id)
    msg = await channel.fetch_message(message_id)
    
    await msg.edit(
        content=f'Last update: {datetime.datetime.now().strftime("%H:%M")}',
        embed=embed
    )

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print('Invite bot link to discord (open in browser):\nhttps://discord.com/api/oauth2/authorize?client_id='+ str(bot.user.id) +'&permissions=8&scope=bot\n')
    read_log.start()
    update_status.start()
    annonces.start()

@bot.event
async def on_message(message):
    if message.author == client.user:		#отсеим свои сообщения
        return;
    if message.author.bot:
        return;
    if str(message.channel.id) != crosschat_id:
        return
    if message.content.startswith(''):
        text = ''
        try:
            print(f"[Discord] {message.author.global_name}: {message.content}")
            await send_annonce(f"[Discord] {message.author.global_name}: {message.content}")
            #await message.add_reaction('✅')
        except Exception as e:
            print(f'ERROR send_annonce>>: {e}')

#template admin commands
'''
@bot.slash_command(description="Add SteamID to Whitelist")
async def admin_cmd(ctx: disnake.ApplicationCommandInteraction, steamid: str):
    if ctx.author.guild_permissions.administrator:
        print(f'it admin command')
        try:
            await ctx.send(f'admin command try', ephemeral=True)
        except Exception as e:
            await ctx.send(f'ERROR Adding SteamID', ephemeral=True)
    else:
        await ctx.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)
'''
#template users command
'''
@bot.slash_command(description="Show commands list")
async def help(ctx):
    await ctx.send('**==Support commands==**\n'
    f' Show commands list```{prefix}help```'
    f' Show server status```{prefix}moestatus```'
    f'\n **Need admin rights**\n'
    f' Auto send server status here```{prefix}sendhere```'
    f' Add server to listing```{prefix}serveradd adress:port name```',
    ephemeral=True
    )
'''

#commands
@bot.slash_command(name=f'{command_prefex}_sendhere', description="Set this channel to announce")
async def sendhere(ctx: disnake.ApplicationCommandInteraction):
    if ctx.author.guild_permissions.administrator:
        try:
            guild = ctx.guild
            print(f'New channel id - {ctx.channel.id}')
            await write_cfg('botconfig', 'channel_id', str(ctx.channel.id))
            channel = await guild.fetch_channel(ctx.channel.id)
            await ctx.response.send_message(content=f'This message for auto updated the status', ephemeral=False)

            last_message = await ctx.channel.fetch_message(ctx.channel.last_message_id)
            print(f'New message id - {last_message.id}')
            await write_cfg('botconfig', 'message_id', str(last_message.id))
            update_settings()

        except Exception as e:
            await ctx.response.send_message(content='❌ An error occurred. Please try again later.', ephemeral=True)
            print(f'Error occurred during file write: {e}')
    else:
        await ctx.response.send_message(content='❌ You do not have permission to run this command.', ephemeral=True)



@bot.slash_command(name=f'{command_prefex}_status', description="Request Servers status")
async def status(ctx: disnake.ApplicationCommandInteraction, ip: str = None, query: int = None):
    try:
        if ip is not None and query is not None:
            info, players, rules = await get_info((f"{ip}", int(query)))
        else:
            info, players, rules = await get_info(address)
        message = (
            f":earth_africa: Direct Link: **{ip}:{info.port}**\n"
            f":link: Invite: **{rules.get('SU_s', 'N/A')}**\n"
            f":map: Map: **{info.map_name}**\n"
            f":green_circle: Online: **{info.player_count}/{info.max_players}**\n"
            f":asterisk: Pass: **{info.password_protected}**\n"
            f":newspaper: Ver: **{rules.get('NO_s', 'N/A')}**\n"
        )
        addition_embed = disnake.Embed(
            title=f"**{info.server_name}**",
            colour=disnake.Colour.green()
        )
        addition_embed.add_field(name="", value=message, inline=False)

        try:
            await ctx.response.send_message(embed=addition_embed, ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f'❌ Failed to send the status message. \nError:\n{e}', ephemeral=True)
            print(f'Error occurred during sending message: {e}')

    except Exception as e:
        await ctx.response.send_message(content='❌ An error occurred. Please try again later.', ephemeral=True)
        print(f'Error occurred during fetching server info: {e}')

@bot.slash_command(name=f'{command_prefex}_players', description="Request Players status")
async def players(ctx: disnake.ApplicationCommandInteraction, ip: str = None, query: int = None):
    try:
        if ip is not None and query is not None:
            info, players, rules = await get_info((f"{ip}", int(query)))
        else:
            info, players, rules = await get_info(address)
    except Exception as e:
        await ctx.response.send_message(content='❌ An error occurred. Please try again later.', ephemeral=True)
        print(f'Error occurred during fetching server info: {e}')

    lists = []
    print(f'\n=== Players List ===')
    for i, player in enumerate(players):
        normal_time = datetime.datetime.utcfromtimestamp(player.duration).strftime('%H:%M:%S')
        print(f"    {player.name}, Time: {normal_time}")
        lists.append(f"\\({i+1}\\) **{player.name}** : {normal_time}")

    def chunk_list(input_list, max_length):
        chunks = []
        current_chunk = ""
        for item in input_list:
            if len(current_chunk) + len(item) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = item + "\n"
            else:
                current_chunk += item + "\n"
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    player_chunks = chunk_list(lists, 1020)

    for i, chunk in enumerate(player_chunks):
        addition_embed = disnake.Embed(
            title=f"Players List {i+1}\nOnline	**{info.player_count}/{info.max_players}**",
            colour=disnake.Colour.blurple()
        )
        addition_embed.add_field(name=f"Players	-	Online Time", value=chunk, inline=False)

        try:
            if i == 0:
                await ctx.response.defer(ephemeral=True)
            await ctx.send(embed=addition_embed, ephemeral=True)
        except Exception as e:
            await ctx.response.send_message(f'❌ Error sending player status. \nError:\n{e}', ephemeral=True)
            print(f'Error occurred during sending player status: {e}')

try:
    bot.run(token)
except disnake.errors.LoginFailure:
    print(' Improper token has been passed.\n Get valid app token https://discord.com/developers/applications/ \nscreenshot https://junger.zzux.com/webhook/guide/4.png')
except disnake.HTTPException:
    print(' HTTPException Discord API')
except disnake.ConnectionClosed:
    print(' ConnectionClosed Discord API')
except disnake.errors.PrivilegedIntentsRequired:
    print(' Privileged Intents Required\n See Privileged Gateway Intents https://discord.com/developers/applications/ \nscreenshot http://junger.zzux.com/webhook/guide/3.png')
