import json
import os
import platform
from typing import Dict, Any
from screeninfo import get_monitors

class ConfigManager:
    """설정 저장 및 불러오기를 관리하는 클래스"""

    def __init__(self, config_path: str = 'km_share_config.json'):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")

        # 기본 설정 반환
        return self.get_default_config()

    def save_config(self):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        screen_info = self.get_screen_info()

        return {
            'local': {
                'name': platform.node(),
                'os': platform.system(),
                'screen_width': screen_info['width'],
                'screen_height': screen_info['height']
            },
            'remote': {
                'ip': '',
                'port': 12345,
                'name': '',
                'os': '',
                'screen_width': 1920,
                'screen_height': 1080
            },
            'layout': {
                'position': 'right',  # left, right, top, bottom
            },
            'features': {
                'edge_detection': True,
                'auto_switch': True,
                'hide_cursor': True,
                'share_clipboard': False
            },
            'network': {
                'discovery_enabled': True,
                'port': 12345
            }
        }

    @staticmethod
    def get_screen_info() -> Dict[str, int]:
        """현재 화면 정보 가져오기"""
        try:
            monitors = get_monitors()
            if monitors:
                # 주 모니터 선택 (첫 번째)
                monitor = monitors[0]
                return {
                    'width': monitor.width,
                    'height': monitor.height
                }
        except Exception as e:
            print(f"Failed to get screen info: {e}")

        # 기본값
        return {'width': 1920, 'height': 1080}

    def get(self, key_path: str, default=None):
        """중첩된 키 경로로 값 가져오기 (예: 'local.name')"""
        keys = key_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value):
        """중첩된 키 경로로 값 설정"""
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value
        self.save_config()

    def update_local_screen_info(self):
        """로컬 화면 정보 업데이트"""
        screen_info = self.get_screen_info()
        self.set('local.screen_width', screen_info['width'])
        self.set('local.screen_height', screen_info['height'])

    def update_remote_from_discovery(self, ip: str, peer_info: Dict):
        """검색된 peer 정보로 원격 설정 업데이트"""
        self.set('remote.ip', ip)
        self.set('remote.name', peer_info.get('name', ''))
        self.set('remote.os', peer_info.get('os', ''))
        self.set('remote.screen_width', peer_info.get('screen_width', 1920))
        self.set('remote.screen_height', peer_info.get('screen_height', 1080))
