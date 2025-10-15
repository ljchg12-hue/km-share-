# KM Share - Keyboard & Mouse Sharing

네트워크를 통해 키보드와 마우스 입력을 공유하는 프로그램입니다.

## 구조

- `src/client.py` - 클라이언트 (입력을 받는 쪽)
- `src/server.py` - 서버 (입력을 보내는 쪽)
- `src/events.py` - 이벤트 직렬화/역직렬화

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

### 서버 실행 (입력을 보내는 컴퓨터)
```bash
python -m src.server
```

### 클라이언트 실행 (입력을 받는 컴퓨터)
```bash
python -m src.client
```

## 설정

`config.json` 파일에서 서버 주소와 포트를 설정할 수 있습니다.

```json
{
  "server": {
    "host": "192.168.0.20",
    "port": 12345
  }
}
```
