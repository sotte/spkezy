import pytest
from spkezy import daemon

pytestmark = pytest.mark.unit


def test_get_notification_command_uses_notify_send_on_linux(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    command = daemon.get_notification_command("Title", "Message")

    assert command == ["notify-send", "-u", "normal", "-t", "2000", "Title", "Message"]


def test_get_notification_command_uses_osascript_on_macos(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    command = daemon.get_notification_command("Title", "Message")

    assert command[0] == "osascript"
    assert command[1] == "-e"
    assert "display notification" in command[2]
    assert '"Message"' in command[2]
    assert '"Title"' in command[2]


def test_get_sound_command_uses_paplay_on_linux(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    sound_file = tmp_path / "sound.mp3"
    sound_file.write_text("x", encoding="utf-8")
    command = daemon.get_sound_command(sound_file)

    assert command == ["paplay", str(sound_file)]


def test_get_sound_command_uses_afplay_on_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    sound_file = tmp_path / "sound.mp3"
    sound_file.write_text("x", encoding="utf-8")
    command = daemon.get_sound_command(sound_file)

    assert command == ["afplay", str(sound_file)]


def test_get_autotype_command_uses_wtype_on_linux(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "linux")

    command = daemon.get_autotype_command("hello", delay_ms=10)

    assert command == ["wtype", "-d", "10", "hello"]


def test_get_autotype_command_uses_osascript_on_macos(monkeypatch):
    monkeypatch.setattr(daemon.sys, "platform", "darwin")

    command = daemon.get_autotype_command("hello", delay_ms=10)

    assert command[0] == "osascript"
    assert command[1] == "-e"
    assert "System Events" in command[2]
    assert 'keystroke "hello"' in command[2]
