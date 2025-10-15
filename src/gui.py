import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from src.config_manager import ConfigManager
from src.discovery import NetworkDiscovery
from src.peer import KMPeer

class KMShareGUI:
    """KM-Share GUI 애플리케이션"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KM-Share - Keyboard & Mouse Sharing")
        self.root.geometry("750x750")
        self.root.resizable(True, True)

        # 설정 관리자
        self.config = ConfigManager()

        # 네트워크 검색
        self.discovery = NetworkDiscovery()
        self.discovery.add_callback(self._on_peer_discovered)

        # P2P peer
        self.peer = None

        # 주기적 브로드캐스트 스레드
        self.broadcast_thread = None
        self.broadcast_running = False

        # GUI 생성
        self._create_widgets()
        self._load_config_to_gui()

        # 종료 핸들러
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        """GUI 위젯 생성"""

        # 상단: 로컬 정보
        local_frame = ttk.LabelFrame(self.root, text="Local Computer", padding=10)
        local_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(local_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.local_name_var = tk.StringVar(value=self.config.get('local.name', ''))
        ttk.Label(local_frame, textvariable=self.local_name_var).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(local_frame, text="OS:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.local_os_var = tk.StringVar(value=self.config.get('local.os', ''))
        ttk.Label(local_frame, textvariable=self.local_os_var).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(local_frame, text="Screen:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.local_screen_var = tk.StringVar(
            value=f"{self.config.get('local.screen_width')}x{self.config.get('local.screen_height')}"
        )
        ttk.Label(local_frame, textvariable=self.local_screen_var).grid(row=1, column=1, sticky=tk.W)

        # 중간: 원격 컴퓨터 연결
        remote_frame = ttk.LabelFrame(self.root, text="Remote Computer", padding=10)
        remote_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 네트워크 검색
        search_frame = ttk.Frame(remote_frame)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Button(search_frame, text="Search Network", command=self._start_discovery).pack(side=tk.LEFT, padx=5)
        self.discovery_status_var = tk.StringVar(value="Not searching")
        ttk.Label(search_frame, textvariable=self.discovery_status_var).pack(side=tk.LEFT)

        # 발견된 peer 리스트
        ttk.Label(remote_frame, text="Discovered Peers:").pack(anchor=tk.W, pady=(10, 0))

        peers_frame = ttk.Frame(remote_frame)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.peers_listbox = tk.Listbox(peers_frame, height=5)
        self.peers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.peers_listbox.bind('<<ListboxSelect>>', self._on_peer_selected)

        scrollbar = ttk.Scrollbar(peers_frame, orient=tk.VERTICAL, command=self.peers_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.peers_listbox.config(yscrollcommand=scrollbar.set)

        # 수동 IP 입력
        manual_frame = ttk.Frame(remote_frame)
        manual_frame.pack(fill=tk.X, pady=5)

        ttk.Label(manual_frame, text="Manual IP:").pack(side=tk.LEFT, padx=5)
        self.manual_ip_var = tk.StringVar(value=self.config.get('remote.ip', ''))
        ttk.Entry(manual_frame, textvariable=self.manual_ip_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Button(manual_frame, text="Connect", command=self._connect_manual).pack(side=tk.LEFT)

        # 화면 배치 선택
        layout_frame = ttk.LabelFrame(self.root, text="Screen Layout", padding=10)
        layout_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(layout_frame, text="Remote screen position:").pack(side=tk.LEFT, padx=5)

        self.layout_var = tk.StringVar(value=self.config.get('layout.position', 'right'))
        positions = [
            ("Right", "right"),
            ("Left", "left"),
            ("Top", "top"),
            ("Bottom", "bottom")
        ]

        for text, value in positions:
            ttk.Radiobutton(layout_frame, text=text, variable=self.layout_var,
                            value=value, command=self._on_layout_changed).pack(side=tk.LEFT, padx=5)

        # 기능 옵션
        features_frame = ttk.LabelFrame(self.root, text="Features", padding=10)
        features_frame.pack(fill=tk.X, padx=10, pady=5)

        self.edge_detection_var = tk.BooleanVar(value=self.config.get('features.edge_detection', True))
        ttk.Checkbutton(features_frame, text="Edge Detection (Auto Switch)",
                        variable=self.edge_detection_var,
                        command=self._on_feature_changed).pack(anchor=tk.W)

        self.hide_cursor_var = tk.BooleanVar(value=self.config.get('features.hide_cursor', True))
        ttk.Checkbutton(features_frame, text="Hide Cursor on Inactive Screen",
                        variable=self.hide_cursor_var,
                        command=self._on_feature_changed).pack(anchor=tk.W)

        # 하단: 상태 및 제어
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 상태 표시
        self.status_var = tk.StringVar(value="Disconnected")
        status_label = ttk.Label(control_frame, textvariable=self.status_var, font=('Arial', 10, 'bold'))
        status_label.pack(side=tk.LEFT, padx=10)

        # 제어 상태 표시
        self.control_status_var = tk.StringVar(value="Local Control")
        control_label = ttk.Label(control_frame, textvariable=self.control_status_var,
                                   font=('Arial', 10), foreground='blue')
        control_label.pack(side=tk.LEFT, padx=10)

        # 시작/중지 버튼
        self.start_button = ttk.Button(control_frame, text="Start", command=self._start_sharing)
        self.start_button.pack(side=tk.RIGHT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self._stop_sharing, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=5)

        # 로그 영역
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _load_config_to_gui(self):
        """설정을 GUI에 로드"""
        # 로컬 정보를 자동으로 갱신
        import platform
        self.config.set('local.name', platform.node())
        self.config.set('local.os', platform.system())
        self.config.update_local_screen_info()

        # GUI에 표시
        self.local_name_var.set(self.config.get('local.name', ''))
        self.local_os_var.set(self.config.get('local.os', ''))
        self.local_screen_var.set(
            f"{self.config.get('local.screen_width')}x{self.config.get('local.screen_height')}"
        )

    def _start_discovery(self):
        """네트워크 검색 시작"""
        self.log("Starting network discovery...")
        self.discovery_status_var.set("Searching...")
        self.peers_listbox.delete(0, tk.END)

        self.discovery.start_listening()

        # 주기적으로 브로드캐스트
        self.broadcast_running = True
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.broadcast_thread.start()

        # 5초 후 자동 중지
        self.root.after(5000, self._stop_discovery)

    def _stop_discovery(self):
        """네트워크 검색 중지"""
        self.broadcast_running = False
        self.discovery.stop_listening()
        self.discovery_status_var.set(f"Found {len(self.discovery.get_discovered_peers())} peers")
        self.log(f"Discovery completed. Found {len(self.discovery.get_discovered_peers())} peers.")

    def _broadcast_loop(self):
        """주기적으로 브로드캐스트"""
        while self.broadcast_running:
            self.discovery.broadcast_presence(
                self.config.get('local.name', ''),
                self.config.get('local.os', ''),
                self.config.get('local.screen_width', 1920),
                self.config.get('local.screen_height', 1080)
            )
            time.sleep(1)

    def _on_peer_discovered(self, ip: str, peer_info: dict):
        """Peer 발견시 호출"""
        self.root.after(0, lambda: self._add_peer_to_list(ip, peer_info))

    def _add_peer_to_list(self, ip: str, peer_info: dict):
        """Peer를 리스트에 추가"""
        peer_str = f"{ip} - {peer_info['name']} ({peer_info['os']}) [{peer_info['screen_width']}x{peer_info['screen_height']}]"

        # 중복 확인
        for i in range(self.peers_listbox.size()):
            if self.peers_listbox.get(i).startswith(ip):
                return

        self.peers_listbox.insert(tk.END, peer_str)
        self.log(f"Discovered peer: {peer_str}")

    def _on_peer_selected(self, event):
        """리스트에서 peer 선택시"""
        selection = self.peers_listbox.curselection()
        if not selection:
            return

        peer_str = self.peers_listbox.get(selection[0])
        ip = peer_str.split(' - ')[0]

        # 설정 업데이트
        peers = self.discovery.get_discovered_peers()
        if ip in peers:
            self.config.update_remote_from_discovery(ip, peers[ip])
            self.manual_ip_var.set(ip)
            self.log(f"Selected peer: {ip}")

    def _connect_manual(self):
        """수동 IP로 연결"""
        ip = self.manual_ip_var.get().strip()
        if not ip:
            messagebox.showwarning("Warning", "Please enter an IP address")
            return

        self.config.set('remote.ip', ip)
        self.log(f"Manual IP set to: {ip}")

    def _on_layout_changed(self):
        """화면 배치 변경시"""
        layout = self.layout_var.get()
        self.config.set('layout.position', layout)
        self.log(f"Screen layout changed to: {layout}")

        if self.peer:
            self.peer.layout_position = layout

    def _on_feature_changed(self):
        """기능 옵션 변경시"""
        self.config.set('features.edge_detection', self.edge_detection_var.get())
        self.config.set('features.hide_cursor', self.hide_cursor_var.get())

    def _start_sharing(self):
        """공유 시작"""
        if not self.config.get('remote.ip'):
            messagebox.showwarning("Warning", "Please select or enter a remote IP address")
            return

        self.log("Starting KM-Share...")

        # P2P peer 생성 및 시작
        self.peer = KMPeer(self.config)
        self.peer.on_connection_changed = self._on_connection_changed
        self.peer.on_control_changed = self._on_control_changed
        self.peer.start()

        # 버튼 상태 변경
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.status_var.set("Connecting...")

    def _stop_sharing(self):
        """공유 중지"""
        self.log("Stopping KM-Share...")

        if self.peer:
            self.peer.stop()
            self.peer = None

        # 버튼 상태 변경
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

        self.status_var.set("Disconnected")
        self.control_status_var.set("Local Control")

    def _on_connection_changed(self, connected: bool):
        """연결 상태 변경시"""
        def update():
            if connected:
                self.status_var.set("Connected")
                self.log("Connected to remote peer!")
            else:
                self.status_var.set("Disconnected")
                self.log("Disconnected from remote peer")

        self.root.after(0, update)

    def _on_control_changed(self, has_control: bool):
        """제어권 변경시"""
        def update():
            if has_control:
                self.control_status_var.set("Local Control")
                self.log("Control: LOCAL")
            else:
                self.control_status_var.set("Remote Control")
                self.log("Control: REMOTE")

        self.root.after(0, update)

    def log(self, message: str):
        """로그 메시지 추가"""
        def add_log():
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)

        if threading.current_thread() != threading.main_thread():
            self.root.after(0, add_log)
        else:
            add_log()

    def _on_closing(self):
        """윈도우 종료시"""
        if self.peer:
            self.peer.stop()

        self.discovery.stop_listening()
        self.broadcast_running = False

        self.root.destroy()

    def run(self):
        """GUI 실행"""
        self.root.mainloop()


def main():
    app = KMShareGUI()
    app.run()


if __name__ == "__main__":
    main()
