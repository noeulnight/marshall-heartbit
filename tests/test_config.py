import pytest

import marshall_heartbit as marshall


def test_config_and_payloads(monkeypatch):
    monkeypatch.setenv("MARSHALL_MAC", "00:12:6F:12:C2:EC")
    assert marshall.config() == ("00:12:6F:12:C2:EC", 32, 60, 8080)
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
    with pytest.raises(ValueError, match="five integers"):
        marshall.setting_payload("equalizer", {"bands": [11] * 5})
