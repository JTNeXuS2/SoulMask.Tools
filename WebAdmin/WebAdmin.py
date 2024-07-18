import base64
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
from urllib.parse import urlparse, unquote

# Port/Username/password for basic web authentication
webserverport = 80
USERNAME = "admin"
PASSWORD = "123456"
#buttons EchoPorts/names for connect to 127.0.0.1, add more if u have more servers
button_ports = '''
    <button onclick=\"sendCommand(20779)\">Send PVE</button>
    <button onclick=\"sendCommand(20712)\">Send PVP</button>
'''
#commands and names
commands_list = '''
    <option value='help'>Help</option>
    <option value='log'>Log</option>
    <option value='dpp'>Get All players</option>
    <option value='saveworld 0'>Fast Save, only actors</option>
    <option value='BackupDatabase world'>Force Save World to disk</option>
    <option value='shutdown 30'>Shutdown after 30 seconds, use SaveWorld before</option>
    <option value='StopCloseServer'>Stop Shutdown</option>

    <option value='QueryInvitationCode'>Get Invitation Code</option>
    <option value='ServerFPS'>Get Server FPS</option>
    <option value='ServerLoginStatus 0'>logging status: Openned</option>
    <option value='ServerLoginStatus 1'>logging status: Close</option>
    <option value='DrawActorImage 0'>Dump the position of the specified type of Actor in the game to the image file: Saved/ACTOR_IMAGE_*.bmp </option>
    <option value='Dump_AllActorPositions'>Export the positions of various Actors in the game to the file: Saved/ACTOR_POSI_DATA.log</option>

    <option value='GetAll WS.HPlayerState PlayerName'>Online players Names</option>
    <option value='GetAll WS.HPlayerState UniqueId'>Online players SteamID</option>
    <option value='GetAll WS.HPlayerState Level'>Online players Level</option>
    <option value='GetAll WS.HPlayerState TotalKeJiPoints'>Online players TotalKeJiPoints</option>
    <option value='GetAll WS.HPlayerState Exp'>Online players Exp</option>
    <option value='GetAll WS.HPlayerState Level'>Online players Level</option>
    <option value='GetAll BP_GameModeBase_C ServerManagerPassword'>Get Admin Password</option>
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
                            }});
                        }}
                    </script>
                </body>
            </html>""".encode()
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
