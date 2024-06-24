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
    global token, channel_id, message_id , update_time, bot_name, bot_ava, address, command_prefex

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
    try:
        info = a2s.info(address)
        players = a2s.players(address)
        rules = a2s.rules(address)
        return info, players, rules
    except Exception as e:
        #print(f"An error occurred while getting server info: {e}")
        channel = await bot.fetch_channel(channel_id)
        message = await channel.fetch_message(message_id)
        embed = disnake.Embed(
            title=f"**{address[0]}:{address[1]}**",
            colour=disnake.Colour.red(),
            description=f"offline or cannot answer",
        )
        await message.edit(content=f'Last update: {datetime.datetime.now().strftime("%H:%M")}', embed=embed)


@tasks.loop(seconds=int(update_time))
async def update_status():
    try:
        info, players, rules = await get_info(address)
        player_count = len(players)
        max_players = info.max_players
        activity = disnake.Game(name=f"Online:{player_count}/{max_players}")
        await bot.change_presence(status=disnake.Status.online, activity=activity)
    
        if bot.user.name != bot_name:
            await bot.user.edit(username=f"{bot_name}")

            response = requests.get(bot_ava)
            data = response.content
            await bot.user.edit(avatar=data)
            '''
            response = requests.get(bot_banner)
            data = response.content
            await bot.user.edit(banner=data)
            ''' 
        async def upd_msg():
            update_settings()
            message = (
                f":earth_africa:Direct Link: **{address[0]}:{info.port}**\n"
                f":link: Invite: **{rules['SU_s']}**\n"
                f":map: Map: **{info.map_name}**\n"
                f":green_circle: Online: **{info.player_count}/{info.max_players}**\n"
                f":asterisk: Pass: **{info.password_protected}**\n"
                f":newspaper: Ver: **{rules['NO_s']}**\n"
                )
            addition_embed = disnake.Embed(
                title=f"**{info.server_name}**",
                colour=disnake.Colour.green(),
                description=f"{message}",
            )
            try:
                channel = await bot.fetch_channel(channel_id)
                message = await channel.fetch_message(message_id)

                if message:
                    await message.edit(content=f'Last update: {datetime.datetime.now().strftime("%H:%M")}', embed=addition_embed)
            except Exception as e:
                print(f'Failed to fetch channel, message or server data. Maybe try /{command_prefex}_sendhere\n {e}')
        await upd_msg()
    except Exception as e:
        print(f'Cant connect to server, check ip and query port \na2s info: {e}')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print('Invite bot link to discord (open in browser):\nhttps://discord.com/api/oauth2/authorize?client_id='+ str(bot.user.id) +'&permissions=8&scope=bot\n')
    await update_status.start()

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
async def status(ctx: disnake.ApplicationCommandInteraction, server_ip: str = None, query_port: int = None):
    if server_ip is None:
        server_ip = address[0]
    try:
        if server_ip is not None and query_port is not None:
            info, players, rules = await get_info((f"{server_ip}", int(query_port)))
        else:
            info, players, rules = await get_info(address)
        message = (
            f":earth_africa: Direct Link: **{server_ip}:{info.port}**\n"
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
async def players(ctx: disnake.ApplicationCommandInteraction, server_ip: str = None, query_port: int = None):
    if server_ip is None:
        server_ip = address[0]
    try:
        if server_ip is not None and query_port is not None:
            info, players, rules = await get_info((f"{server_ip}", int(query_port)))
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
