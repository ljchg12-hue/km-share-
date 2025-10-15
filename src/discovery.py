import socket
import json
import threading
import time
from typing import List, Dict, Callable

class NetworkDiscovery:
    """네트워크에서 다른 KM-Share 인스턴스를 찾는 클래스"""

    BROADCAST_PORT = 12346
    MAGIC_STRING = "KM_SHARE_DISCOVERY"

    def __init__(self, port: int = BROADCAST_PORT):
        self.port = port
        self.discovered_peers: Dict[str, Dict] = {}  # {ip: {name, os, screen_res}}
        self.running = False
        self.listen_thread = None
        self.callbacks: List[Callable] = []
        self.local_ips = self._get_local_ips()

    def _get_local_ips(self) -> List[str]:
        """로컬 IP 주소 목록 가져오기"""
        local_ips = ['127.0.0.1']
        try:
            # 모든 네트워크 인터페이스의 IP 가져오기
            hostname = socket.gethostname()
            local_ips.append(socket.gethostbyname(hostname))

            # 추가로 모든 인터페이스 확인
            import netifaces
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr.get('addr')
                        if ip and ip not in local_ips:
                            local_ips.append(ip)
        except:
            pass

        return local_ips

    def add_callback(self, callback: Callable):
        """새 peer 발견시 호출될 콜백 추가"""
        self.callbacks.append(callback)

    def start_listening(self):
        """브로드캐스트 수신 시작"""
        if self.running:
            return

        self.running = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()

    def stop_listening(self):
        """브로드캐스트 수신 중지"""
        self.running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)

    def _listen_loop(self):
        """브로드캐스트 메시지 수신 루프"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.port))
        sock.settimeout(1.0)

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))

                if message.get('magic') == self.MAGIC_STRING:
                    peer_ip = addr[0]

                    # 자기 자신의 IP는 무시
                    if peer_ip in self.local_ips:
                        continue

                    peer_info = {
                        'name': message.get('name', 'Unknown'),
                        'os': message.get('os', 'Unknown'),
                        'screen_width': message.get('screen_width', 0),
                        'screen_height': message.get('screen_height', 0),
                        'timestamp': time.time()
                    }

                    # 새로운 peer이거나 정보가 업데이트된 경우
                    if peer_ip not in self.discovered_peers:
                        self.discovered_peers[peer_ip] = peer_info
                        for callback in self.callbacks:
                            callback(peer_ip, peer_info)
                    else:
                        self.discovered_peers[peer_ip] = peer_info

            except socket.timeout:
                continue
            except Exception as e:
                print(f"Discovery listen error: {e}")

        sock.close()

    def broadcast_presence(self, name: str, os_name: str, screen_width: int, screen_height: int):
        """자신의 존재를 브로드캐스트"""
        message = {
            'magic': self.MAGIC_STRING,
            'name': name,
            'os': os_name,
            'screen_width': screen_width,
            'screen_height': screen_height
        }

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        try:
            data = json.dumps(message).encode('utf-8')
            sock.sendto(data, ('<broadcast>', self.port))
        except Exception as e:
            print(f"Broadcast error: {e}")
        finally:
            sock.close()

    def get_discovered_peers(self) -> Dict[str, Dict]:
        """발견된 peer 목록 반환"""
        # 30초 이상 오래된 peer는 제거
        current_time = time.time()
        expired = [ip for ip, info in self.discovered_peers.items()
                   if current_time - info['timestamp'] > 30]
        for ip in expired:
            del self.discovered_peers[ip]

        return self.discovered_peers.copy()
