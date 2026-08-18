import pytest

import marshall_heartbit as marshall


def test_config_and_payloads(monkeypatch):
    monkeypatch.setenv("MARSHALL_MAC", "00:12:6F:12:C2:EC")
    assert marshall.config() == ("00:12:6F:12:C2:EC", 32, 60, 8080)
    monkeypatch.setenv("HEARTBEAT_INTERVAL", "0")
    assert marshall.config() == ("00:12:6F:12:C2:EC", 32, 0, 8080)
    assert marshall.setting_payload("volume", {"value": 32}) == (
        marshall.VOLUME_UUID,
        b"\x20",
    )
    assert marshall.setting_payload("source", {"value": "aux"})[1] == b"\x0d"
    assert marshall.setting_payload("interaction-sounds", {"enabled": False})[1] == b"\x10"
    assert marshall.setting_payload("equalizer", {"bands": [1, 2, 3, 4, 5]})[1] == bytes(
        [1, 2, 3, 4, 5]
    )
    assert marshall.setting_payload("light", {"value": 69})[1] == b"\x45"
    assert marshall.setting_payload("name", {"value": "ACTON II"})[1] == b"\x01\x08ACTON II"
    assert marshall.setting_value("volume", b"\x20") == 32
    assert marshall.setting_value("source", bytes([1, 0, 0, 1, 1])) == "aux"
    assert marshall.setting_value("source", bytes([3, 2, 0, 1, 1])) == "bluetooth"
    assert marshall.setting_value("interaction-sounds", bytes([3, 2, 0, 0, 1])) is False
    assert marshall.setting_value("equalizer", bytes([1, 2, 3, 4, 5])) == [1, 2, 3, 4, 5]
    assert marshall.setting_value("light", b"\x45") == 69
    assert marshall.setting_value("name", b"\x01\x08ACTON II") == "ACTON II"
    assert marshall.volume_from_percent(50) == 16
    assert marshall.volume_percent(16) == 50
    assert marshall.volume_from_percent(100) == 32
    with pytest.raises(ValueError, match="five integers"):
        marshall.setting_payload("equalizer", {"bands": [11] * 5})
