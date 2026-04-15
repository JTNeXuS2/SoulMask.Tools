import os
import base64
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse, unquote, parse_qs

# Port/Username/password for basic web authentication
webserverport = 8080
USERNAME = "admin"
PASSWORD = "WEB_PASSWORD"
#buttons ports/names for connect to 127.0.0.1, add more if u have more servers
button_ports = '''
    <button onclick=\"sendCommand(810)\">Send PVP</button>
    <button style="background-color: #303090;" onclick=\"sendbase_path('C:/wgsm/servers/1/serverfiles/WS/Saved')\">Files PVP</button>

    <button onclick=\"sendCommand(779)\">Send PVE</button>
    <button style="background-color: #303090;" onclick=\"sendbase_path('C:/wgsm/servers/9/serverfiles/WS/Saved')\">Files PVE</button>

    <button onclick=\"sendCommand(833)\">Send PVE_DLC</button>
    <button style="background-color: #303090;" onclick=\"sendbase_path('C:/wgsm/servers/10/serverfiles/WS/Saved')\">Files PVE_DLC</button>

    <button onclick=\"sendCommand(20702)\">Send TEST</button>

'''
#commands and names
commands_list = '''
    <option value=''> </option>
    <option value='ListPlayers'>Table List Players</option>
    <option value=''> </option>
    <option value='ShowHelp'> View Help </option>
    <option value='log'>Log</option>
    <option value='saveworld 0'>Fast Save, only actors</option>
    <option value='BackupDatabase world'>Force Save World to disk</option>
    <option value='close 30'> Save World And ShutDown </option>
    <option value='shutdown 30'>Shutdown after 30 seconds, use SaveWorld before</option>
    <option value='StopCloseServer'>Stop Shutdown</option>
    <option value=''> </option>

    <option value='lp'> List Online Players </option>
    <option value='lap'> List all Players </option>
    <option value='ls STEAM_ID_or_character_UID'> List owned belonging objects </option>
    <option value='lg'> List guilds </option>
    <option value='lgo guild_name_or_guild_UID'> List guilds objects (with one arg: guild's name or guild's uid) </option>
    <option value='lcc'> List all npc names and class names </option>
    <option value='lcc Core'> List all npc names and class names (with one string arg [optional], if not empty, results should contains the arg) </option>
    <option value='lc'> List the game settings (Show_GameXishu) </option>
    <option value='GetAll WS.HPlayerState PlayerName'>Online players Names</option>
    <option value='GetAll WS.HPlayerState UniqueId'>Online players SteamID</option>
    <option value='GetAll WS.HPlayerState Level'>Online players Level</option>
    <option value='GetAll WS.HPlayerState TotalKeJiPoints'>Online players TotalKeJiPoints</option>
    <option value='GetAll WS.HPlayerState Exp'>Online players Exp</option>
    <option value='GetAll BP_GameModeBase_C ServerManagerPassword'>Get Admin Password</option>
    <option value=''> </option>

    <option value='ssp 1 1'>Enable Ban List</option>
    <option value='usp 1 1 STEAM_ID'>Ban Player</option>
    <option value='usp 1 0 STEAM_ID'>UnBan Player</option>

    <option value='ssp 4 1'>Enable Mute List</option>
    <option value='usp 4 1 STEAM_ID'>Mute Player</option>
    <option value='usp 4 0 STEAM_ID'>UnMute Player</option>
    <option value=''> </option>

    <option value='cnpc SteamID 2 1'>Create Template barbarian (Owner SteamID)(Num 0-999), (0 male, 1 female)</option>
    <option value='create SteamID Class is_bady level nums quality'>Creates Actor (for list class use lcc)</option>
    <option value='create SteamID /Game/Blueprints/AI/Ren/BP_BuLuo_Base.BP_BuLuo_Base_C 0 60 1 5'>Creates Thrall (for list class use lcc)</option>
    <option value='create SteamID /Game/Blueprints/DongWu/BP_DongWu_BaoZi.BP_DongWu_BaoZi_C 0 60 1 5'>Creates Jaguar (for list class use lcc)</option>
    <option value=''> </option>

    <option value='gonpc Name_UID_AccountNumber Name_UID_AccountNumber'> Teleport character1 to character2 </option>
    <option value='go Name_UID_AccountNumber 225518 33773 40290'> Teleport character1 to x y z  (portal)</option>
    <option value='fly steam_ID 1'>Set the player's fly-mode ON </option>
    <option value='fly steam_ID 0'>Set the player's fly-mode OFF </option>
    <option value=''> </option>

    <option value='QueryInvitationCode'>Get Invitation Code</option>
    <option value='ServerFPS'>Get Server FPS</option>
    <option value='ServerLoginStatus 0'>logging status: Openned</option>
    <option value='ServerLoginStatus 1'>logging status: Close</option>
    <option value='DrawActorImage 0'>Dump the position of the specified type of Actor in the game to the image file: Saved/ACTOR_IMAGE_*.bmp </option>
    <option value='Dump_AllActorPositions'>Export the positions of various Actors in the game to the file: Saved/ACTOR_POSI_DATA.log</option>
    <option value='QueryGridCount'> QueryGridCount </option>
    <option value='DrawGrids'> draw grids to WS/Saved/GRID_IMAGE_*.PPM </option>
    <option value=''> </option>

    <option value='sc Setting Value'> Set the game coefficient (Set_GameXishu) Example: [sc ExpRatio 5.0] </option>
    <option value='ssp 4 1'> Enable/Disable list, 0 Account whitelist, 1 Account blocked, 2 IP whitelist, 3 IP blocked, 4 Muted list, [ssp 4 1] Enable Mute list </option>
    <option value='lsp'> View the server permissions list (List_ServerPermissionList) </option>
    <option value='Set_OutputChats 1'> Enable/Disable Chat Output world/nearby/guild to the LOG file (Set 0 to disable) </option>
    <option value=''> </option>
'''


#not change any more
html_auth = '''
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Авторизация</title>
        </head>
        <body>
            <h1>Authentication</h1>
            <form action="/login" method="post">
                <label for="username">Login:</label>
                <input type="text" id="username" name="username" required><br>
                <label for="password">Pass:</label>
                <input type="password" id="password" name="password" required><br>
                <input type="submit" value="Enter">
            </form>
        </body>
        </html>
        '''
html = f"""<html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        table {{
                            font-family: Arial, sans-serif;
                            border-collapse: collapse;
                            width: 100%;
                        }}

                        table td, table th {{
                            border: 1px solid #dddddd;
                            text-align: left;
                            padding: 8px;
                        }}

                        table th {{
                            background-color: #f2f2f2;
                        }}

                        button {{
                            margin-top: 10px;
                            padding: 10px 20px;
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            cursor: pointer;
                        }}
                        
                        /* Стили для индикатора загрузки */
                        .loader {{
                            display: inline-block;
                            width: 20px;
                            height: 20px;
                            border: 3px solid #f3f3f3;
                            border-top: 3px solid #3498db;
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                            margin-left: 10px;
                        }}
                        
                        @keyframes spin {{
                            0% {{ transform: rotate(0deg); }}
                            100% {{ transform: rotate(360deg); }}
                        }}
                        
                        .loading-text {{
                            color: #666;
                            font-style: italic;
                            margin: 10px 0;
                            padding: 10px;
                            background-color: #f0f0f0;
                            border-radius: 5px;
                        }}
                        
                        .response-container {{
                            margin-top: 20px;
                            padding: 10px;
                            border: 1px solid #ddd;
                            border-radius: 5px;
                            background-color: #f9f9f9;
                        }}
                    </style>
                </head>
                <body>
                    <div>
                        <label for='command'>Enter command:</label>
                        <input type='text' id='command' style='width: 100%;'>
                        <label for='commandSelect'>Select command:</label>
                        <select id='commandSelect' onchange='updateCommandField()'>
                            {commands_list}
                        </select>
                    </div>
                    <p>
                        {button_ports}
                    </p>
                    <div class="response-container">
                        <div id="loadingIndicator" style="display: none;">
                            <span class="loading-text">⏳ Выполняется команда, пожалуйста, подождите...</span>
                            <div class="loader"></div>
                        </div>
                        <pre id='file_list'></pre>
                        <pre id='response'></pre>
                    </div>
                    <script>

                        function updateCommandField() {{
                            var selectedCommand = document.getElementById('commandSelect').value;
                            document.getElementById('command').value = selectedCommand;
                        }}

                        function showLoading() {{
                            document.getElementById('loadingIndicator').style.display = 'block';
                            document.getElementById('response').innerHTML = '';
                            document.getElementById('file_list').innerHTML = '';
                        }}

                        function hideLoading() {{
                            document.getElementById('loadingIndicator').style.display = 'none';
                        }}

                        async function sendCommand(port) {{
                            var command = document.getElementById('command').value;
                            
                            if (!command.trim()) {{
                                alert('Пожалуйста, введите команду');
                                return;
                            }}
                            
                            showLoading();
                            
                            try {{
                                // Для ListPlayers используем специальную обработку
                                if (command === 'ListPlayers') {{
                                    const response = await fetch('/send_request?command=' + command + '&port=' + port);
                                    const data = await response.text();
                                    hideLoading();
                                    document.getElementById('response').innerHTML = data;
                                    document.getElementById('file_list').innerHTML = '';
                                }} else {{
                                    const response = await fetch('/send_request?command=' + command + '&port=' + port);
                                    const data = await response.text();
                                    hideLoading();
                                    var lines = data.split('\\n');
                                    var formattedText = '';
                                    lines.forEach(line => formattedText += line + '\\n');
                                    document.getElementById('response').innerText = formattedText;
                                    document.getElementById('file_list').innerHTML = '';
                                }}
                            }} catch (error) {{
                                hideLoading();
                                document.getElementById('response').innerHTML = '<span style="color: red;">❌ Ошибка: ' + error.message + '</span>';
                            }}
                        }}
                        
                        async function sendbase_path(base_path) {{
                            showLoading();
                            
                            try {{
                                const response = await fetch('/files_list?base_path=' + base_path);
                                const data = await response.text();
                                hideLoading();
                                var lines = data.split('\\n');
                                var formattedText = '';
                                lines.forEach(line => formattedText += line + '\\n');
                                document.getElementById('response').innerHTML = '';
                                document.getElementById('file_list').innerHTML = formattedText;
                            }} catch (error) {{
                                hideLoading();
                                document.getElementById('file_list').innerHTML = '<span style="color: red;">❌ Ошибка: ' + error.message + '</span>';
                            }}
                        }}
                        
                    </script>
                </body>
            </html>"""

class WebHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(30)  # например, 30 секунд

    def send_telnet_command(self, port, command):
        command = unquote(command)
        send = f"cmd.exe /c echo {command}|plink.exe -telnet 127.0.0.1 -P {port} -raw -batch"
        process = subprocess.Popen(send, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            output, error = process.communicate(timeout=10)  # 10 секунд таймаут
        except subprocess.TimeoutExpired:
            process.kill()
            output, error = process.communicate()
            return ["Error: plink command timed out."]
        
        if output:
            output_str = output.decode('utf-8', errors='replace')
            cleaned_text = output_str.replace("Hello:\r\n", "").replace("Type help for command list.\r\n", "")
            return cleaned_text.split('\n')
        if error:
            return [error.decode('utf-8', errors='replace')]
        return []

    def get_players_list(self, port):
        """Получает и сопоставляет данные игроков с сервера"""
        # Получаем UniqueId (Steam ID)
        response_id = self.send_telnet_command(port, "GetAll WS.HPlayerState UniqueId")
        # Получаем PlayerName
        response_name = self.send_telnet_command(port, "GetAll WS.HPlayerState PlayerName")
        # Получаем Level
        response_level = self.send_telnet_command(port, "GetAll WS.HPlayerState Level")
        
        players = {}
        
        # Парсим UniqueId
        for line in response_id:
            # Ищем паттерн: HPlayerState_123456789.UniqueId = 76561198206843371
            if 'HPlayerState_' in line and '.UniqueId =' in line:
                try:
                    # Извлекаем ID (число между HPlayerState_ и .UniqueId)
                    id_part = line.split('HPlayerState_')[1].split('.UniqueId')[0]
                    # Извлекаем Steam ID
                    steam_id = line.split('= ')[1].strip()
                    players[id_part] = {'ID': id_part, 'SteamID': steam_id, 'PlayerName': '', 'Level': ''}
                except:
                    pass
        
        # Парсим PlayerName
        for line in response_name:
            if 'HPlayerState_' in line and '.PlayerName =' in line:
                try:
                    id_part = line.split('HPlayerState_')[1].split('.PlayerName')[0]
                    name = line.split('= ')[1].strip()
                    if id_part in players:
                        players[id_part]['PlayerName'] = name
                except:
                    pass
        
        # Парсим Level
        for line in response_level:
            if 'HPlayerState_' in line and '.Level =' in line:
                try:
                    id_part = line.split('HPlayerState_')[1].split('.Level')[0]
                    level = line.split('= ')[1].strip()
                    if id_part in players:
                        players[id_part]['Level'] = level
                except:
                    pass
        
        return players

    def format_players_table(self, players):
        """Форматирует список игроков в HTML таблицу"""
        if not players:
            return "<p>📭 Нет игроков онлайн</p>"
        
        html_table = """
        <style>
            .players-table {
                font-family: Arial, sans-serif;
                border-collapse: collapse;
                width: 100%;
                margin-top: 20px;
            }
            .players-table th, .players-table td {
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }
            .players-table th {
                background-color: #4CAF50;
                color: white;
            }
            .players-table tr:nth-child(even) {
                background-color: #f2f2f2;
            }
        </style>
        <h2>📊 List Online players</h2>
        <table class="players-table">
            <tr>
                <th>ID</th>
                <th>Steam ID</th>
                <th>Player Name</th>
                <th>Level</th>
            </tr>
        """
        
        for player_id, data in players.items():
            if data.get('PlayerName'):  # Показываем только игроков с именем (онлайн)
                html_table += f"""
                <tr>
                    <td>{data.get('ID', '')}</td>
                    <td>{data.get('SteamID', '')}</td>
                    <td>{data.get('PlayerName', '')}</td>
                    <td>{data.get('Level', '')}</td>
                </tr>
                """
        
        html_table += "</table>"
        return html_table

    def do_GET(self):
        parsed_path = urlparse(self.path)
        cookies = SimpleCookie(self.headers.get('Cookie', ''))

        # Check cookie
        is_authenticated = 'authenticated' in cookies and cookies['authenticated'].value == 'true'

        if parsed_path.path == '/':
            if not is_authenticated:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return
        
            # Create Main Page
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return
            
        elif parsed_path.path == '/login':
            if is_authenticated:
                # Redirect if auth
                self.send_response(302)
                self.send_header('Location', '/')
                self.end_headers()
                return
            self.send_login_form()
            return

        elif parsed_path.path == '/send_request':
            if not is_authenticated:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            query_params = parse_qs(parsed_path.query)
            command = query_params.get('command', [''])[0]
            port = query_params.get('port', [''])[0]
            
            # Новая обработка для ListPlayers
            if command == 'ListPlayers':
                players = self.get_players_list(int(port))
                response_html = self.format_players_table(players)
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(response_html.encode('utf-8'))
                return
            
            # Старая обработка для остальных команд
            response = self.send_telnet_command(int(port), command)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            for line in response:
                self.wfile.write(f"{line}\n".encode('utf-8'))
            return

        elif parsed_path.path.startswith('/files_list'):
            if not is_authenticated:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            query_params = parse_qs(parsed_path.query)
            base_path = query_params.get('base_path', [''])[0]
            if os.path.isdir(base_path):
                files = os.listdir(base_path)

                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()

                files_html = f'<h1>Files in Directory: {base_path}</h1><ul>'
                for file in files:
                    file_path = os.path.join(base_path, file)
                    if os.path.isfile(file_path):
                        file_link = f'<a href="/download?base_path={base_path}&file={file}" download>{file}</a>'
                        files_html += f'<li>{file_link}</li>'
                files_html += '</ul>'

                self.wfile.write(files_html.encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'Directory not found')
            return

        elif parsed_path.path == '/download':
            if not is_authenticated:
                self.send_response(302)
                self.send_header('Location', '/login')
                self.end_headers()
                return

            query_params = parse_qs(parsed_path.query)
            file_name = query_params.get('file', [''])[0]
            base_path = query_params.get('base_path', [''])[0]
            file_path = os.path.join(base_path, file_name)

            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{file_name}"')
                self.end_headers()

                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(b'File not found')
            return

    def do_POST(self):
        if self.path == '/login':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            form_data = parse_qs(post_data.decode('utf-8'))
            username = form_data.get('username', [None])[0]
            password = form_data.get('password', [None])[0]

            if username == USERNAME and password == PASSWORD:
                # Auth Success
                self.send_response(302)
                self.send_header('Set-Cookie', 'authenticated=true; Path=/')
                self.send_header('Location', '/')
                self.end_headers()
            else:
                # Try Again
                self.send_response(401)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(b"<h1>Wrong User Name or Password!</h1> <button onclick=\"window.location.href='/login'\">Try again</button>")
            return

    def send_login_form(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_auth.encode('utf-8'))

def run(server_class=HTTPServer, handler_class=WebHandler, port=webserverport):
    while True:
        try:
            server_address = ('', port)
            httpd = server_class(server_address, handler_class)
            print(f"Starting HTTP server on port {port}")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('Stopping server by user request...')
            break  # Выход из цикла и завершение программы
        except Exception as e:
            print(f"Server error: {e}. Restarting in 5 seconds...")
            time.sleep(5)


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print('Stoping...')
