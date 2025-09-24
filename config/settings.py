# config/settings.py
import yaml

def load_config(path: str = 'config.yaml') -> dict:
    try:
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError("Configuration file config.yaml not found!")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Error parsing YAML file: {e}")

settings = load_config()
CLIENT_CONFIG = settings.get('clients', {})
TIER_KEYS = settings.get('tier_keys', {})