import socket
import json
from pynput import mouse, keyboard
from src.events import deserialize_event

class KMClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()

    def start(self):
        self.client_socket.connect((self.host, self.port))
        print(f"Connected to server at {self.host}:{self.port}")

        buffer = b''
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break

                buffer += data
                # Split by newline to handle multiple messages
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line:
                        try:
                            event = deserialize_event(line)
                            self.handle_event(event)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}, data: {line}")
            except socket.error as e:
                print(f"Socket error: {e}")
                break

    def handle_event(self, event):
        event_type = event.get('type')
        if event_type == 'mouse_move':
            self.mouse_controller.position = (event['x'], event['y'])
        elif event_type == 'mouse_button':
            button_map = {
                'Button.left': mouse.Button.left,
                'Button.right': mouse.Button.right,
                'Button.middle': mouse.Button.middle,
            }
            button = button_map.get(event['button'])
            if button:
                if event['pressed']:
                    self.mouse_controller.press(button)
                else:
                    self.mouse_controller.release(button)
        elif event_type == 'mouse_scroll':
            self.mouse_controller.scroll(event['dx'], event['dy'])
        elif event_type == 'keyboard':
            key_str = event['key']
            # This is a simplified mapping. A full mapping would be more complex.
            key = None
            if 'Key.' in key_str:
                key = getattr(keyboard.Key, key_str.split('.')[-1], None)
            else:
                key = key_str

            if key:
                if event['pressed']:
                    self.keyboard_controller.press(key)
                else:
                    self.keyboard_controller.release(key)

if __name__ == "__main__":
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        server_config = config.get('server', {})
        host = server_config.get('host', 'localhost')
        port = server_config.get('port', 12345)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Using default config: localhost:12345")
        host = 'localhost'
        port = 12345

    client = KMClient(host, port)
    client.start()
