import base64
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from urllib.parse import urlparse, unquote
import os

# Port/Username/password for basic web authentication
webserverport = 80
USERNAME = "admin"
PASSWORD = "123456"
#buttons EchoPorts/names for connect to 127.0.0.1, add more if u have more servers
button_ports = '''
    <button onclick=\"sendCommand(20779)\">Send PVE</button>
    <button onclick=\"sendCommand(20712)\">Send PVP</button>
    <button style="background-color: #303090;" onclick=\"sendbase_path('C:/wgsm/servers/2/serverfiles/WS/Saved')\">Files PVPX5</button>
'''
#commands and names
commands_list = '''
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
    <option value='GetAll WS.HPlayerState Level'>Online players Level</option>
    <option value='GetAll BP_GameModeBase_C ServerManagerPassword'>Get Admin Password</option>
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
html = f"""<html>
                <head>
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
                    <div>
                        <pre id='file_list'></pre>
                        <pre id='response'></pre>
                    </div>
                    <script>

                        function updateCommandField() {{
                            var selectedCommand = document.getElementById('commandSelect').value;
                            document.getElementById('command').value = selectedCommand;
                        }}

                        function sendCommand(port) {{
                            var command = document.getElementById('command').value;
                            fetch('/send_request?command=' + command + '&port=' + port).then(response => response.text()).then(data => {{
                                var lines = data.split('\\n');
                                var formattedText = '';
                                lines.forEach(line => formattedText += line + '\\n');
                                document.getElementById('response').innerText = formattedText;
                                document.getElementById('file_list').innerText = '';
                            }});
                        }}
                        
                        function sendbase_path(base_path) {{
                            fetch('/files_list?base_path=' + base_path).then(response => response.text()).then(data => {{
                                var lines = data.split('\\n');
                                var formattedText = '';
                                lines.forEach(line => formattedText += line + '\\n');
                                document.getElementById('response').innerText = '';
                                document.getElementById('file_list').innerHTML = formattedText;
                            }});
                        }}
                        
                    </script>
                </body>
            </html>""".encode()
import os

class WebHandler(BaseHTTPRequestHandler):

    def send_telnet_command(self, port, command):
        command = unquote(command)
        send = f"cmd.exe /c echo {command}|plink.exe -telnet 127.0.0.1 -P {port} -raw -batch"
        process = subprocess.Popen(send, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if output:
            output_str = output.decode('utf-8')
            cleaned_text = output_str.replace("Hello:\r\n", "")
            cleaned_text = cleaned_text.replace("Type help for command list.\r\n", "")
            return cleaned_text.split('\n')  # split text into lines
        if error:
            error = error.decode('utf-8')
            return [error]

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/':
            if not self.check_auth():
                self.send_auth_headers()
                return

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            self.wfile.write(html)
            return

        elif parsed_path.path == '/send_request':
            if not self.check_auth():
                self.send_auth_headers()
                return

            query_params = urllib.parse.parse_qs(parsed_path.query)
            command = query_params.get('command', [''])[0]
            port = query_params.get('port', [''])[0]
            response = self.send_telnet_command(int(port), command)

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            if response is None:
                self.wfile.write(f"server did not return anything\n".encode())
                return
            for line in response:
                self.wfile.write(f"{line}\n".encode())

            return

        elif parsed_path.path.startswith('/files_list'):
            if not self.check_auth():
                self.send_auth_headers()
                return

            query_params = urllib.parse.parse_qs(parsed_path.query)
            directory_name = query_params.get('directory', [''])[0]
            base_path = query_params.get('base_path', [''])[0]
            if os.path.isdir(base_path):
                files = os.listdir(base_path)

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                # Generate HTML for the list of files in the directory with correct download links
                files_html = f'<h1>Files in Directory: {base_path}</h1><ul>'
                for file in files:
                    file_path = os.path.join(base_path, file)
                    if os.path.isfile(file_path):
                        file_link = f'<a href="/download?base_path={base_path}&file={file}" download>{file}</a>'
                        files_html += f'<li>{file_link}</li>'
                files_html += '</ul>'

                self.wfile.write(files_html.encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Directory not found')
            return

            
        elif parsed_path.path == '/download':
            if not self.check_auth():
                self.send_auth_headers()
                return

            query_params = urllib.parse.parse_qs(parsed_path.query)
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
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
            return

    def check_auth(self):
        auth_header = self.headers.get('Authorization')
        if auth_header:
            encoded_credentials = auth_header.split(' ')[1]
            credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = credentials.split(':')
            return username == USERNAME and password == PASSWORD
        return False

    def send_auth_headers(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Secure Area"')
        self.end_headers()
        self.wfile.write(b"Authorization Required")

def run(server_class=HTTPServer, handler_class=WebHandler, port=webserverport):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting HTTP server on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
if __name__ == '__main__':
    run()
