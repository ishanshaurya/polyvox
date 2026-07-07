"""Shared config load, template merge, and API key resolution."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

_ENV_LOADED = False


def repo_root() -> Path:
    """Repository root."""
    return Path(__file__).resolve().parents[4]


def _load_dotenv() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = repo_root() / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def default_config_path() -> str:
    env = os.environ.get("PIPELINE_CONFIG", "").strip()
    if env:
        return env
    root = repo_root()
    for candidate in ("config.yaml", "configs/example.yaml"):
        if (root / candidate).is_file():
            return candidate
    return "config.yaml"


def _resolve_template_name(cfg: dict) -> str | None:
    if cfg.get("analysis_template"):
        return str(cfg["analysis_template"])
    profile = (cfg.get("analysis_profile") or "").lower()
    if profile == "generic":
        return "healthcare"
    # Any other profile name maps straight to templates/<profile>.yaml —
    # site-specific templates are local-only, not committed (see .gitignore).
    if profile:
        return profile
    return None


def _merge_template(cfg: dict) -> dict:
    template_name = _resolve_template_name(cfg)
    if not template_name:
        return cfg
    path = repo_root() / "templates" / f"{template_name}.yaml"
    if not path.is_file():
        return cfg
    with open(path, encoding="utf-8") as f:
        template_cfg = yaml.safe_load(f) or {}
    merged = dict(template_cfg)
    merged.update(cfg)
    return merged


def _merge_local_overrides(cfg: dict, config_path: str) -> dict:
    """Merge `config.local.yaml` next to the loaded config, if present.

    Never committed (see .gitignore) — the place for site-specific values
    (client display name, legacy filename markers, hospital names, hold-music
    phrases) that shouldn't appear in the public repo.
    """
    local_path = Path(config_path).parent / "config.local.yaml"
    if not local_path.is_file():
        return cfg
    with open(local_path, encoding="utf-8") as f:
        overrides = yaml.safe_load(f) or {}
    merged = dict(cfg)
    merged.update(overrides)
    return merged


def load_config(path: str | None = None) -> dict:
    _load_dotenv()
    config_path = path or default_config_path()
    if not Path(config_path).is_absolute():
        config_path = str(repo_root() / config_path)
    with open(config_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg = _merge_local_overrides(cfg, config_path)
    return _merge_template(cfg)


def agent_eval_min_calls(cfg: dict) -> int:
    return int(cfg.get("agent_eval_min_calls", 3))


def ensure_api_key(cfg: dict) -> str:
    _load_dotenv()
    key = (cfg.get("anthropic_api_key") or "").strip()
    if key and not key.startswith("paste"):
        os.environ["ANTHROPIC_API_KEY"] = key
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "\nERROR: Anthropic API key not set. Set ANTHROPIC_API_KEY in .env or config.\n"
        )
    return key


def resolve_groq_api_key(cfg: dict) -> str:
    _load_dotenv()
    key = (cfg.get("groq_api_key") or "").strip()
    if not key:
        key = os.environ.get("GROQ_API_KEY", "").strip()
    return key


def ensure_groq_api_key(cfg: dict) -> str:
    key = resolve_groq_api_key(cfg)
    if not key:
        raise SystemExit(
            "\nERROR: Groq API key not set. Set GROQ_API_KEY in .env or config.\n"
        )
    os.environ["GROQ_API_KEY"] = key
    return key


def resolve_assemblyai_api_key(cfg: dict) -> str:
    _load_dotenv()
    key = (cfg.get("assemblyai_api_key") or "").strip()
    if not key:
        key = os.environ.get("ASSEMBLYAI_API_KEY", "").strip()
    return key


def ensure_assemblyai_api_key(cfg: dict) -> str:
    key = resolve_assemblyai_api_key(cfg)
    if not key:
        raise SystemExit(
            "\nERROR: AssemblyAI API key not set. Set ASSEMBLYAI_API_KEY in .env or config.\n"
        )
    import assemblyai as aai

    aai.settings.api_key = key
    return key
