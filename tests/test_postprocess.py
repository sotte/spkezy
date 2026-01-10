import pytest
from spkezy import postprocess

pytestmark = pytest.mark.unit


class LogSpy:
    def __init__(self):
        self.warnings: list[tuple[str, dict]] = []

    def warning(self, event: str, **kwargs):
        self.warnings.append((event, kwargs))


def test_load_postprocess_config_parses_supported_fields(monkeypatch, tmp_path):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(
        """
[postprocess_llm]
enabled = true
provider = "openai"
model = "gpt-4o-mini"
preferred_terms = ["alpha", 2, "beta"]
prompt_override = "Custom prompt"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = postprocess.load_postprocess_config()

    assert config.enabled is True
    assert config.provider == "openai"
    assert config.model == "gpt-4o-mini"
    assert config.preferred_terms == ["alpha", "beta"]
    assert config.prompt_override == "Custom prompt"


def test_load_postprocess_config_ignores_blank_prompt_override(monkeypatch, tmp_path):
    config_dir = tmp_path / "spkezy"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(
        """
[postprocess_llm]
prompt_override = "   "
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    config = postprocess.load_postprocess_config()

    assert config.prompt_override is None


@pytest.mark.parametrize(
    "preferred_terms, expected_snippet",
    [
        (["alpha", "beta"], "Preferred terms (use when ambiguous):"),
        ([], "Transcript:\nHello"),
    ],
)
def test_build_user_prompt_includes_preferred_terms_when_present(preferred_terms, expected_snippet):
    prompt = postprocess._build_user_prompt("Hello", preferred_terms)

    assert expected_snippet in prompt


def test_postprocess_transcript_returns_original_when_disabled():
    config = postprocess.PostprocessConfig(enabled=False)

    result = postprocess.postprocess_transcript("Hello", config)

    assert result == "Hello"


def test_postprocess_transcript_returns_original_when_provider_unsupported():
    config = postprocess.PostprocessConfig(enabled=True, provider="other")
    log = LogSpy()

    result = postprocess.postprocess_transcript("Hello", config, log)

    assert result == "Hello"
    assert log.warnings


def test_postprocess_transcript_returns_original_when_api_key_missing(monkeypatch):
    config = postprocess.PostprocessConfig(enabled=True, provider="openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    log = LogSpy()

    result = postprocess.postprocess_transcript("Hello", config, log)

    assert result == "Hello"
    assert log.warnings


def test_postprocess_transcript_returns_original_when_transcript_blank(monkeypatch):
    config = postprocess.PostprocessConfig(enabled=True, provider="openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = postprocess.postprocess_transcript("   ", config)

    assert result == "   "
