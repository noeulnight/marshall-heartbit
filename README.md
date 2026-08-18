# Marshall Heartbit

마샬 스피커에 주기적으로 Bluetooth 연결을 요청해 절전 상태에서 깨우는 Raspberry Pi용
서비스입니다.

ACTON II는 Classic Bluetooth로만 광고하며 Raspberry Pi의 BlueZ에는 오디오 프로필만
노출됩니다. 실제 장치에서 연결과 페어링에 성공했으며, 컨테이너는 system D-Bus의
`org.bluez.Device1.Connect`를 기본 60초마다 호출합니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

호스트에서 BlueZ가 실행 중이어야 합니다. 최초 연결 때 스피커가 페어링 가능한 상태여야
하며 이후에는 저장된 페어링을 재사용합니다.
