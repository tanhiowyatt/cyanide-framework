import json
import datetime
import asyncio
from typing import Dict

# Import dependencies (handle circular imports carefully if needed)
# Here we assume these are available
from cyanide.core.geoip import GeoIP
from cyanide.core.stats import StatsManager

class AnalyticsService:
    """
    Handles ML analysis, GeoIP enrichment, and statistics.
    """
    def __init__(self, config: Dict, logger):
        self.config = config
        self.logger = logger
        self.stats = StatsManager()
        self.geoip = GeoIP()
        
        # ML Initialization
        self.ml_enabled = config.get("ml", {}).get("enabled", False)
        self.ml_online_learning = config.get("ml", {}).get("online_learning", False)
        self.ml_filter = None
        self.kb = None
        
        if self.ml_enabled:
            self._init_ml()

    def _init_ml(self):
        try:
            from pathlib import Path
            from cyanide.ml.cyanideML import HoneypotFilter
            from cyanide.ml.cyanideML.knowledge_base import KnowledgeBase
            
            config_path = self.config.get("ml", {}).get("model_path", "src/cyanide/ml/cyanideML/cyanideML.pkl")
            model_path = Path(config_path)
            
            if model_path.exists():
                self.logger.log_event("system", "system_status", {"message": f"Loading pre-trained ML model from {model_path}..."})
                self.ml_filter = HoneypotFilter.load(str(model_path))
                self.ml_filter.online_learning = self.ml_online_learning
            else:
                self.logger.log_event("system", "system_warning", {"message": "Pre-trained model not found, starting fresh (WARMUP mode)."})
                self.ml_filter = HoneypotFilter(online_learning=self.ml_online_learning)
                
            self.ml_log_path = self.config.get("ml", {}).get("ml_log", "var/log/cyanide/cyanideML-log.json")
            
            # Load Knowledge Base
            self.kb = KnowledgeBase()
            kb_file = model_path.parent / "knowledge_base.pkl"
            if kb_file.exists():
                self.kb.load(str(kb_file))
            else:
                self.logger.log_event("system", "error", {"message": f"Knowledge Base file not found at {kb_file}"})
                
        except (ImportError, ModuleNotFoundError) as e:
            self.logger.log_event("system", "error", {"message": f"ML Module could not be loaded: {e}"})
            self.ml_enabled = False
        except Exception as e:
            self.logger.log_event("system", "error", {"message": f"Failed to init ML model: {e}"})
            self.ml_enabled = False

    def analyze_command(self, cmd: str, username: str, src_ip: str, session_id: str, protocol: str):
        """Run command through ML filter and alert if anomaly."""
        if not self.ml_enabled or not self.ml_filter:
            return

        try:
            # Construct log entry format expected by filter
            log_entry = {
                "command": cmd,
                "username": username,
                "src_ip": src_ip,
                "dst_port": self.config.get(protocol, {}).get("port", 0), # Best effort
                "protocol": protocol
            }
            
            is_anomaly, reason, distance = self.ml_filter.process_log(log_entry)
            
            # Log ML 'thought' for every action
            ml_log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "src_ip": src_ip,
                "session_id": session_id,
                "verdict": "anomaly" if is_anomaly else "clean",
                "reason": reason,
                "distance": float(distance),
                "command": cmd
            }
            
            # Enrich with Knowledge Base if anomaly
            if is_anomaly and self.kb:
                kb_results = self.kb.search(cmd)
                if kb_results:
                    ml_log_entry["kb_correlation"] = kb_results
                    # Add display string logic if needed...
            
            with open(self.ml_log_path, "a") as f:
                f.write(json.dumps(ml_log_entry) + "\n")

            if is_anomaly:
                asyncio.create_task(self.logger.log_event_async({
                    "event": "ml_anomaly",
                    "reason": reason,
                    "distance": distance,
                    "cmd": cmd,
                    "src_ip": src_ip
                }))
                
        except Exception as e:
            self.logger.log_event(session_id, "error", {"message": f"ML Error: {e}"})

    async def log_geoip(self, session_id: str, ip: str, protocol: str):
        """Async GeoIP enrichment logging."""
        geo_data = await self.geoip.lookup(ip)
        if geo_data:
            await self.logger.log_event_async({
                "event": "client_geo", "session_id": session_id,
                "protocol": protocol, "src_ip": ip,
                "geo": geo_data
            })
