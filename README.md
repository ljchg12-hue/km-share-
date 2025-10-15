# KM-Share - Keyboard & Mouse Sharing

**Mouse without Borders** 스타일의 크로스 플랫폼 키보드/마우스 공유 애플리케이션

## 기능

- 🖱️ **화면 경계 자동 전환**: 마우스가 화면 끝에 도달하면 자동으로 다른 PC로 전환
- 🔍 **자동 네트워크 검색**: 같은 네트워크의 다른 KM-Share 인스턴스 자동 발견
- 🎯 **유연한 화면 배치**: 좌/우/상/하 화면 배치 선택 가능
- 💻 **크로스 플랫폼**: Windows, Linux 지원
- 🔒 **P2P 통신**: 직접 연결로 낮은 지연시간
- ⚙️ **GUI 설정**: 쉬운 설정 및 관리

## 요구사항

- Python 3.7+
- 라이브러리:
  - pynput (키보드/마우스 제어)
  - screeninfo (화면 정보)
  - netifaces (네트워크 인터페이스)

## 설치

1. 저장소 클론 또는 다운로드

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

## 사용법

### GUI 모드 (권장)

```bash
python km_share.py
```

### 사용 단계

1. **양쪽 컴퓨터에서 실행**
   - 리눅스와 윈도우 PC 양쪽에서 `km_share.py` 실행

2. **네트워크 검색**
   - "Search Network" 버튼 클릭
   - 발견된 peer 목록에서 상대방 PC 선택

3. **화면 배치 설정**
   - 상대방 화면의 위치 선택 (Left/Right/Top/Bottom)
   - 예: 윈도우 PC가 오른쪽에 있다면 "Right" 선택

4. **연결 시작**
   - "Start" 버튼 클릭
   - 연결 완료 후 화면 경계로 마우스를 이동시켜 테스트

### 수동 IP 입력

- 네트워크 검색이 실패한 경우, "Manual IP" 필드에 상대방 IP 입력 후 "Connect"

## 화면 배치 예시

```
리눅스 왼쪽, 윈도우 오른쪽:
┌──────────┐  ┌──────────┐
│ Linux    │→ │ Windows  │
│          │  │          │
└──────────┘  └──────────┘

리눅스 설정: Remote position = "Right"
윈도우 설정: Remote position = "Left"
```

## 설정 파일

설정은 자동으로 `km_share_config.json`에 저장됩니다.

```json
{
  "local": {
    "name": "my-computer",
    "os": "Linux",
    "screen_width": 1920,
    "screen_height": 1080
  },
  "remote": {
    "ip": "192.168.0.13",
    "port": 12345
  },
  "layout": {
    "position": "right"
  },
  "features": {
    "edge_detection": true,
    "auto_switch": true,
    "hide_cursor": true
  }
}
```

## 트러블슈팅

### 연결이 안 되는 경우

1. **방화벽 확인**
   - 포트 12345 (기본값) 허용 확인

2. **같은 네트워크 확인**
   - 양쪽 PC가 같은 네트워크에 있는지 확인

3. **수동 IP 입력**
   - 자동 검색 대신 수동으로 IP 입력

### 마우스가 전환되지 않는 경우

1. **Edge Detection 활성화 확인**
   - Features에서 "Edge Detection" 체크박스 확인

2. **화면 배치 확인**
   - 양쪽 PC의 화면 배치 설정이 올바른지 확인

## 개발 정보

- **프로토콜**: TCP (포트 12345)
- **검색**: UDP 브로드캐스트 (포트 12346)
- **메시지 포맷**: JSON + newline 구분자

## 라이선스

MIT License
