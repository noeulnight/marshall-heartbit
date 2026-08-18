# Marshall Heartbit

마샬 스피커의 볼륨 characteristic에 주기적으로 값을 써서 절전 상태에서 깨우는
Raspberry Pi용 BLE 서비스입니다.

ACTON II 패킷 캡처에서 확인한 characteristic UUID
`44FA50B2-D0A3-472E-A939-D80CF17638BB`에 기본값 `0x1E`를 60초마다 Write Request로
전송합니다. 볼륨 범위는 0–30입니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

호스트에서 BlueZ가 실행 중이어야 합니다.
