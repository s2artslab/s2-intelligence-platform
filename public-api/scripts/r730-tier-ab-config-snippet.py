# Snippet to append to unified_egregore_service/config.py (Tier A/B inference)

# Tier A — decoding & prompt defaults (match training: no persona by default)
DEFAULT_USE_PERSONA = os.environ.get("EGREGORE_USE_PERSONA", "0") == "1"
DEFAULT_DO_SAMPLE = os.environ.get("EGREGORE_DO_SAMPLE", "0") == "1"
DEFAULT_TEMPERATURE = float(os.environ.get("EGREGORE_DEFAULT_TEMPERATURE", "0.2"))
DEFAULT_MAX_NEW_TOKENS = int(os.environ.get("EGREGORE_MAX_NEW_TOKENS", "150"))
# stacked = merge foundation then ake; egregore_only = ake on base (training had only ake adapter active)
ADAPTER_LOAD_MODE = os.environ.get("EGREGORE_ADAPTER_LOAD_MODE", "egregore_only")
