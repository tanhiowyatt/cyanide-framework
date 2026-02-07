import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from cyanide.core.config import load_config
config = load_config()
print(f"MITRE CVE PATH: {config['ml']['training_data']['mitre_cve']}")
