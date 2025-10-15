import socket
import json
import threading
import time
from pynput import mouse, keyboard
from src.events import serialize_event, deserialize_event
from typing import Callable, Optional

class KMPeer:
    """
    Mouse without Borders 스타일의 P2P 통신 클래스
    양방향 통신 및 화면 경계 감지를 지원
    """

    def __init__(self, config):
        self.config = config
        self.socket = None
        self.running = False
        self.connected = False

        # 제어권 상태
        self.has_control = True  # 시작시 로컬이 제어권 보유

        # 마우스/키보드 컨트롤러
        try:
            self.mouse_controller = mouse.Controller()
            self.keyboard_controller = keyboard.Controller()
            print("Mouse and keyboard controllers initialized")
        except Exception as e:
            print(f"Failed to initialize controllers: {e}")
            print("This may be a permission issue. The application may not work properly.")
            self.mouse_controller = None
            self.keyboard_controller = None

        # 리스너
        self.mouse_listener = None
        self.keyboard_listener = None

        # 네트워크 스레드
        self.listen_thread = None
        self.server_thread = None

        # 콜백
        self.on_connection_changed: Optional[Callable] = None
        self.on_control_changed: Optional[Callable] = None

        # 화면 정보
        self.local_width = config.get('local.screen_width', 1920)
        self.local_height = config.get('local.screen_height', 1080)
        self.remote_width = config.get('remote.screen_width', 1920)
        self.remote_height = config.get('remote.screen_height', 1080)
        self.layout_position = config.get('layout.position', 'right')

        # 마지막 마우스 위치
        self.last_mouse_pos = (0, 0)

        # 제어권 전환 쿨다운
        self.last_transfer_time = 0

    def start(self):
        """P2P 연결 시작"""
        if self.running:
            return

        self.running = True

        # 서버 소켓 시작 (다른 peer의 연결을 받기 위해)
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        # 원격 peer에 연결 시도
        remote_ip = self.config.get('remote.ip')
        if remote_ip:
            threading.Thread(target=self._connect_to_peer, args=(remote_ip,), daemon=True).start()

    def stop(self):
        """P2P 연결 중지"""
        self.running = False
        self._stop_listeners()

        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

        self.connected = False
        if self.on_connection_changed:
            self.on_connection_changed(False)

    def _run_server(self):
        """서버 소켓 실행 (다른 peer의 연결 대기)"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        port = self.config.get('network.port', 12345)
        try:
            server_socket.bind(('0.0.0.0', port))
            server_socket.listen(1)
            server_socket.settimeout(1.0)

            while self.running:
                try:
                    client_socket, addr = server_socket.accept()
                    if not self.connected:  # 아직 연결되지 않은 경우
                        print(f"Peer connected from {addr}")
                        self.socket = client_socket
                        self.connected = True

                        # 서버 역할: 초기 제어권 보유
                        self.has_control = True

                        if self.on_connection_changed:
                            self.on_connection_changed(True)
                        if self.on_control_changed:
                            self.on_control_changed(True)

                        self._start_listeners()
                        self._start_receive_loop()
                    else:
                        client_socket.close()  # 이미 연결된 경우 거부

                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Server accept error: {e}")
                    break

        except Exception as e:
            print(f"Server bind error: {e}")
        finally:
            server_socket.close()

    def _connect_to_peer(self, remote_ip: str):
        """원격 peer에 연결"""
        port = self.config.get('remote.port', 12345)
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            if not self.running or self.connected:
                break

            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((remote_ip, port))

                self.socket = sock
                self.connected = True
                print(f"Connected to peer at {remote_ip}:{port}")

                # 클라이언트 역할: 초기 제어권 보유 (양쪽 모두 초기에 제어 가능)
                self.has_control = True

                if self.on_connection_changed:
                    self.on_connection_changed(True)
                if self.on_control_changed:
                    self.on_control_changed(True)

                # 리스너 시작 (양쪽 모두 입력 가능)
                self._start_listeners()
                self._start_receive_loop()
                break

            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(retry_delay)

    def _start_receive_loop(self):
        """메시지 수신 루프 시작"""
        self.listen_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.listen_thread.start()

    def _receive_loop(self):
        """메시지 수신 루프"""
        buffer = b''

        # 소켓 타임아웃 제거 (블로킹 모드)
        try:
            self.socket.settimeout(None)
        except:
            pass

        while self.running and self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    print("Connection closed by peer")
                    break

                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line:
                        try:
                            event = deserialize_event(line)
                            self._handle_remote_event(event)
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")

            except socket.error as e:
                print(f"Socket error: {e}")
                break

        # 연결 종료
        self.connected = False
        if self.on_connection_changed:
            self.on_connection_changed(False)

    def _handle_remote_event(self, event: dict):
        """원격에서 받은 이벤트 처리"""
        event_type = event.get('type')

        # 제어권 전환 이벤트
        if event_type == 'control_transfer':
            self.has_control = event.get('give_control', False)

            # 제어권을 받을 때 마우스 위치 설정
            if self.has_control:
                cursor_x = event.get('cursor_x', 0)
                cursor_y = event.get('cursor_y', 0)
                if self.mouse_controller:
                    try:
                        self.mouse_controller.position = (cursor_x, cursor_y)
                        time.sleep(0.1)  # 짧은 지연으로 위치 안정화
                    except Exception as e:
                        print(f"Failed to set cursor position: {e}")
                self._start_listeners()
                print(f"Control received, cursor at ({cursor_x}, {cursor_y})")
            else:
                self._stop_listeners()
                print("Control released")

            if self.on_control_changed:
                self.on_control_changed(self.has_control)
            return

        # 제어권이 없을 때만 원격 입력을 처리
        if not self.has_control:
            if event_type == 'mouse_move':
                if self.mouse_controller:
                    # 원격 좌표를 로컬 좌표로 변환
                    x, y = self._remote_to_local_coords(event['x'], event['y'])
                    try:
                        self.mouse_controller.position = (x, y)
                    except Exception as e:
                        print(f"Failed to move mouse: {e}")

            elif event_type == 'mouse_button':
                if self.mouse_controller:
                    button_map = {
                        'Button.left': mouse.Button.left,
                        'Button.right': mouse.Button.right,
                        'Button.middle': mouse.Button.middle,
                    }
                    button = button_map.get(event['button'])
                    if button:
                        try:
                            if event['pressed']:
                                self.mouse_controller.press(button)
                            else:
                                self.mouse_controller.release(button)
                        except Exception as e:
                            print(f"Failed to handle mouse button: {e}")

            elif event_type == 'mouse_scroll':
                if self.mouse_controller:
                    try:
                        self.mouse_controller.scroll(event['dx'], event['dy'])
                    except Exception as e:
                        print(f"Failed to scroll: {e}")

            elif event_type == 'keyboard':
                if self.keyboard_controller:
                    key_str = event['key']
                    key = None
                    if 'Key.' in key_str:
                        key = getattr(keyboard.Key, key_str.split('.')[-1], None)
                    else:
                        key = key_str

                    if key:
                        try:
                            if event['pressed']:
                                self.keyboard_controller.press(key)
                            else:
                                self.keyboard_controller.release(key)
                        except Exception as e:
                            print(f"Failed to handle keyboard: {e}")

    def _start_listeners(self):
        """마우스/키보드 리스너 시작"""
        if self.mouse_listener or self.keyboard_listener:
            return

        try:
            self.mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )

            self.mouse_listener.start()
            self.keyboard_listener.start()
            print("Listeners started successfully")
        except Exception as e:
            print(f"Failed to start listeners: {e}")
            print("This may be a permission issue. Try running with sudo or check X11 access.")
            self.mouse_listener = None
            self.keyboard_listener = None

    def _stop_listeners(self):
        """마우스/키보드 리스너 중지"""
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
                print("Mouse listener stopped")
            except Exception as e:
                print(f"Error stopping mouse listener: {e}")
            self.mouse_listener = None

        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                print("Keyboard listener stopped")
            except Exception as e:
                print(f"Error stopping keyboard listener: {e}")
            self.keyboard_listener = None

    def _on_move(self, x, y):
        """마우스 이동 이벤트"""
        if not self.has_control or not self.connected:
            return

        # 화면 경계 감지 (화면 밖 좌표도 체크)
        if self.config.get('features.edge_detection', True):
            if self._check_edge_trigger(x, y):
                self._transfer_control_to_remote(x, y)
                return

        self.last_mouse_pos = (x, y)

        # 마우스 이동 이벤트 전송
        event = {'type': 'mouse_move', 'x': x, 'y': y}
        self._send_event(event)

    def _on_click(self, x, y, button, pressed):
        """마우스 클릭 이벤트"""
        if not self.has_control or not self.connected:
            return

        event = {'type': 'mouse_button', 'x': x, 'y': y, 'button': str(button), 'pressed': pressed}
        self._send_event(event)

    def _on_scroll(self, x, y, dx, dy):
        """마우스 스크롤 이벤트"""
        if not self.has_control or not self.connected:
            return

        event = {'type': 'mouse_scroll', 'x': x, 'y': y, 'dx': dx, 'dy': dy}
        self._send_event(event)

    def _on_press(self, key):
        """키보드 눌림 이벤트"""
        if not self.has_control or not self.connected:
            return

        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)

        event = {'type': 'keyboard', 'key': key_str, 'pressed': True}
        self._send_event(event)

    def _on_release(self, key):
        """키보드 뗌 이벤트"""
        if not self.has_control or not self.connected:
            return

        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)

        event = {'type': 'keyboard', 'key': key_str, 'pressed': False}
        self._send_event(event)

    def _check_edge_trigger(self, x, y) -> bool:
        """화면 경계 도달 여부 확인"""
        threshold = 20  # 경계로부터 몇 픽셀 이내 (증가)

        # 쿨다운 체크 (0.5초 이내 재전환 방지)
        current_time = time.time()
        if current_time - self.last_transfer_time < 0.5:
            return False

        if self.layout_position == 'right':
            # 오른쪽 경계 또는 오른쪽을 벗어남
            return x >= self.local_width - threshold
        elif self.layout_position == 'left':
            # 왼쪽 경계 또는 왼쪽을 벗어남 (음수 포함)
            return x <= threshold
        elif self.layout_position == 'bottom':
            # 아래쪽 경계 또는 아래쪽을 벗어남
            return y >= self.local_height - threshold
        elif self.layout_position == 'top':
            # 위쪽 경계 또는 위쪽을 벗어남 (음수 포함)
            return y <= threshold

        return False

    def _transfer_control_to_remote(self, x, y):
        """제어권을 원격으로 넘김"""
        print(f"Transferring control to remote at ({x}, {y})")

        # 쿨다운 타이머 업데이트
        self.last_transfer_time = time.time()

        # 원격 좌표 계산
        remote_x, remote_y = self._local_to_remote_coords(x, y)

        # 제어권 전환 메시지 전송
        self._send_event({
            'type': 'control_transfer',
            'give_control': True,
            'cursor_x': remote_x,
            'cursor_y': remote_y
        })

        # 로컬 제어권 해제
        self.has_control = False
        self._stop_listeners()

        if self.on_control_changed:
            self.on_control_changed(False)

    def _local_to_remote_coords(self, x, y):
        """로컬 좌표를 원격 좌표로 변환"""
        # 좌표를 화면 범위 내로 정규화
        x = max(0, min(x, self.local_width - 1))
        y = max(0, min(y, self.local_height - 1))

        if self.layout_position == 'right':
            # 오른쪽 화면으로 넘어갈 때 → 원격 화면 왼쪽 끝
            remote_x = 150  # 충분히 안쪽으로 (증가)
            remote_y = int(y * self.remote_height / self.local_height)
            return (remote_x, remote_y)
        elif self.layout_position == 'left':
            # 왼쪽 화면으로 넘어갈 때 → 원격 화면 오른쪽 끝
            remote_x = self.remote_width - 150  # 충분히 안쪽으로 (증가)
            remote_y = int(y * self.remote_height / self.local_height)
            return (remote_x, remote_y)
        elif self.layout_position == 'bottom':
            # 아래쪽 화면으로 넘어갈 때 → 원격 화면 위쪽 끝
            remote_x = int(x * self.remote_width / self.local_width)
            remote_y = 150  # 충분히 안쪽으로 (증가)
            return (remote_x, remote_y)
        elif self.layout_position == 'top':
            # 위쪽 화면으로 넘어갈 때 → 원격 화면 아래쪽 끝
            remote_x = int(x * self.remote_width / self.local_width)
            remote_y = self.remote_height - 150  # 충분히 안쪽으로 (증가)
            return (remote_x, remote_y)

        return (x, y)

    def _remote_to_local_coords(self, remote_x, remote_y):
        """원격 좌표를 로컬 좌표로 변환"""
        # 단순 스케일링 (더 정교한 매핑 가능)
        local_x = int(remote_x * self.local_width / self.remote_width)
        local_y = int(remote_y * self.local_height / self.remote_height)
        return (local_x, local_y)

    def _send_event(self, event: dict):
        """이벤트를 원격으로 전송"""
        if not self.connected or not self.socket:
            return

        try:
            self.socket.sendall(serialize_event(event))
        except socket.error as e:
            print(f"Send error: {e}")
            self.connected = False
            if self.on_connection_changed:
                self.on_connection_changed(False)
