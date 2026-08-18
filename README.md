# Marshall API

Raspberry Pi에서 ACTON II를 제어하는 BLE HTTP API입니다. 볼륨 `0x20`을 기본 60초마다
전송하는 heartbeat도 유지합니다.

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

```bash
curl localhost:8080/health
curl -X PUT localhost:8080/settings/volume -H 'content-type: application/json' -d '{"value":32}'
curl -X PUT localhost:8080/settings/source -H 'content-type: application/json' -d '{"value":"bluetooth"}'
curl -X PUT localhost:8080/settings/interaction-sounds -H 'content-type: application/json' -d '{"enabled":true}'
curl -X PUT localhost:8080/settings/equalizer -H 'content-type: application/json' -d '{"bands":[5,5,5,5,5]}'
curl -X PUT localhost:8080/settings/light -H 'content-type: application/json' -d '{"value":69}'
curl -X PUT localhost:8080/settings/name -H 'content-type: application/json' -d '{"value":"ACTON II"}'
curl -X POST localhost:8080/heartbeat
```

볼륨 범위는 0–32, EQ 다섯 밴드는 각각 0–10, LED 밝기는 0–69, 이름은 UTF-8
17바이트까지입니다. 소스는 `bluetooth` 또는 `aux`입니다.

호스트에서 BlueZ가 실행 중이어야 합니다.
