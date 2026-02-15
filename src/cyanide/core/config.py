import configparser
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from .config_schema import CyanideConfig
from pydantic import ValidationError

def load_config(path: Path = Path("config/cyanide.cfg")):
    """Load and normalized configuration from INI file and .env."""
    # Load .env file
    env_path = Path("config/.env")
    load_dotenv(dotenv_path=env_path)

    cfg = configparser.ConfigParser()
    if path.exists():
        cfg.read(path)
    else:
        # If config file is missing, we rely solely on .env or defaults
        print(f"[*] Config file not found at {path}, using .env and defaults.")
        
    def get_val(section, key, env_var, default, cast=str):
        # Priority: Env > Config File > Default
        val = os.getenv(env_var)
        if val is None and cfg.has_section(section):
            val = cfg.get(section, key, fallback=None)
        
        if val is None:
            return default
            
        if cast is bool:
            if isinstance(val, bool):
                return val
            return val.lower() in ('true', '1', 'yes', 'on')
        elif cast is int:
            return int(val)
        return val

    # Convert to dictionary structure expected by HoneypotServer
    config = {
        "hostname": get_val("honeypot", "hostname", "HOSTNAME", "server01"),
        "log_path": get_val("honeypot", "log_path", "LOG_PATH", "var/log/cyanide"),
        "listen_ip": get_val("server", "host", "HOST", "0.0.0.0"),
        "fs_yaml": get_val("honeypot", "fs_yaml", "FS_YAML", None),
        "quarantine_path": get_val("honeypot", "quarantine_path", "DATA_PATH", "var/lib/cyanide/quarantine"),
        "os_profile": get_val("server", "os_profile", "OS_PROFILE", "random"),
        "dns_cache_ttl": get_val("honeypot", "dns_cache_ttl", "DNS_CACHE_TTL", 60, int),
        "max_sessions": get_val("server", "max_sessions", "MAX_SESSIONS", 100, int),
        "max_sessions_per_ip": get_val("server", "max_sessions_per_ip", "MAX_SESSIONS_PER_IP", 5, int),
        "session_timeout": get_val("server", "session_timeout", "SESSION_TIMEOUT", 300, int),
        "quarantine_max_size_mb": get_val("server", "quarantine_max_size_mb", "QUARANTINE_MAX_SIZE_MB", 500, int),
        "ssh": {
            "port": get_val("ssh", "listen_port", "SSH_PORT", 2222, int),
            "enabled": get_val("ssh", "enabled", "SSH_ENABLED", True, bool),
            "backend_mode": get_val("ssh", "backend_mode", "SSH_BACKEND", "emulated"),
            "target_host": get_val("ssh", "target_host", "SSH_TARGET_HOST", "127.0.0.1"),
            "target_port": get_val("ssh", "target_port", "SSH_TARGET_PORT", 22222, int)
        },
        "telnet": {
            "port": get_val("telnet", "listen_port", "TELNET_PORT", 2323, int),
            "enabled": get_val("telnet", "enabled", "TELNET_ENABLED", False, bool),
            "backend_mode": get_val("telnet", "backend_mode", "TELNET_BACKEND", "emulated"),
            "target_host": get_val("telnet", "target_host", "TELNET_TARGET_HOST", "127.0.0.1"),
            "target_port": get_val("telnet", "target_port", "TELNET_TARGET_PORT", 23, int),
            "banner": get_val("telnet", "banner", "TELNET_BANNER", None)
        },
        "metrics": {
            "enabled": get_val("metrics", "enabled", "METRICS_ENABLED", True, bool),
            "port": get_val("metrics", "port", "METRICS_PORT", 9090, int)
        },
        "smtp": {
            "enabled": get_val("smtp", "enabled", "SMTP_ENABLED", False, bool),
            "listen_port": get_val("smtp", "listen_port", "SMTP_PORT", 25, int),
            "target_host": get_val("smtp", "target_host", "SMTP_TARGET_HOST", "127.0.0.1"),
            "target_port": get_val("smtp", "target_port", "SMTP_TARGET_PORT", 2525, int)
        },
        "users": []
    }
    
    # User loading - Env vars for users
    users_env = os.getenv("CYANIDE_USERS")
    if users_env:
        try:
            env_users = json.loads(users_env)
            if isinstance(env_users, list):
                config["users"].extend(env_users)
        except json.JSONDecodeError:
            print("[!] Failed to parse CYANIDE_USERS env var (expected JSON list).")

    if cfg.has_section("users"):
        for username, password in cfg.items("users"):
            config["users"].append({"user": username, "pass": password})
    
    if not config["users"]:
        config["users"] = [{"user": "root", "pass": "admin"}, {"user": "admin", "pass": "admin"}]
        
    config["ml"] = {
        "enabled": get_val("ml", "enabled", "ML_ENABLED", False, bool),
        "ml_log": get_val("ml", "ml_log", "ML_LOG", "var/log/cyanide/cyanideML-log.json"),
        "model_path": get_val("ml", "model_path", "MODEL_PATH", "src/cyanide/ml/cyanideML/cyanideML.pkl"),
        "online_learning": get_val("ml", "online_learning", "ONLINE_LEARNING", False, bool),
        "training_data": {
            "hacker_methods": Path("data/ml_training/hacker_methods"),
            "mitre_cve": Path("data/ml_training/kb_ready")
        }
    }

    config["cleanup"] = {
        "enabled": get_val("cleanup", "enabled", "CLEANUP_ENABLED", True, bool),
        "interval": get_val("cleanup", "interval", "CLEANUP_INTERVAL", 3600, int),
        "retention_days": get_val("cleanup", "retention_days", "CLEANUP_RETENTION_DAYS", 7, int),
        "paths": get_val("cleanup", "paths", "CLEANUP_PATHS", "var/log/cyanide,var/lib/cyanide").split(",")
    }

    # Load Custom Profile metadata if exists
    config["custom_profile"] = {}
    if cfg.has_section("custom_profile"):
        for key in ["name", "ssh_banner", "uname_r", "uname_a", "etc_issue", "proc_version"]:
            config["custom_profile"][key] = cfg.get("custom_profile", key, fallback="")
            
    # Rate Limit
    config["rate_limit"] = {
        "max_connections_per_minute": get_val("rate_limit", "max_connections_per_minute", "RATE_LIMIT_MAX", 60, int),
        "ban_duration": get_val("rate_limit", "ban_duration", "RATE_LIMIT_BAN", 3600, int)
    }

    # OpenTelemetry
    config["otel"] = {
        "enabled": get_val("otel", "enabled", "OTEL_ENABLED", False, bool),
        "exporter": get_val("otel", "exporter", "OTEL_EXPORTER", "otlp"),
        "endpoint": get_val("otel", "endpoint", "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    }

    # VirusTotal
    config["virustotal"] = {
        "enabled": get_val("virustotal", "enabled", "VIRUSTOTAL_ENABLED", False, bool),
        "api_key": get_val("virustotal", "api_key", "VIRUSTOTAL_API_KEY", None)
    }
        
    try:
        model = CyanideConfig(**config)
        return model.model_dump()
    except ValidationError as e:
        print(f"[!] Configuration Error:\n{e}")
        sys.exit(1)
