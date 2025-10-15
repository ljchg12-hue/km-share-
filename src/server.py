import socket
import json
from pynput import mouse, keyboard
from src.events import serialize_event

class KMServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = None

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Server listening on {self.host}:{self.port}")
        self.client_socket, addr = self.server_socket.accept()
        print(f"Accepted connection from {addr}")

        self.start_listeners()

    def send_event(self, event):
        if self.client_socket:
            try:
                self.client_socket.sendall(serialize_event(event))
            except socket.error as e:
                print(f"Socket error: {e}")
                self.client_socket = None

    def on_move(self, x, y):
        # For simplicity, we send the absolute position.
        # A better approach for multi-monitor setups would be relative movement.
        event = {'type': 'mouse_move', 'x': x, 'y': y}
        self.send_event(event)

    def on_click(self, x, y, button, pressed):
        event = {'type': 'mouse_button', 'x': x, 'y': y, 'button': str(button), 'pressed': pressed}
        self.send_event(event)

    def on_scroll(self, x, y, dx, dy):
        event = {'type': 'mouse_scroll', 'x': x, 'y': y, 'dx': dx, 'dy': dy}
        self.send_event(event)

    def on_press(self, key):
        try:
            event = {'type': 'keyboard', 'key': key.char, 'pressed': True}
        except AttributeError:
            event = {'type': 'keyboard', 'key': str(key), 'pressed': True}
        self.send_event(event)

    def on_release(self, key):
        try:
            event = {'type': 'keyboard', 'key': key.char, 'pressed': False}
        except AttributeError:
            event = {'type': 'keyboard', 'key': str(key), 'pressed': False}
        self.send_event(event)

    def start_listeners(self):
        mouse_listener = mouse.Listener(
            on_move=self.on_move,
            on_click=self.on_click,
            on_scroll=self.on_scroll
        )
        keyboard_listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )

        mouse_listener.start()
        keyboard_listener.start()
        mouse_listener.join()
        keyboard_listener.join()

if __name__ == "__main__":
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        server_config = config.get('server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 12345)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Using default config: 0.0.0.0:12345")
        host = '0.0.0.0'
        port = 12345

    server = KMServer(host, port)
    server.start()
