from src.scanner import ProjectScanner
from typing import Dict, Any
import datetime

class KnowledgeSynthesizer:
    """
    Synthesizes project knowledge and security report based on scanned files and detected framework.
    """
    def __init__(self, root_path: str):
        self.scanner = ProjectScanner(root_path)
        self.report: Dict[str, Any] = {}

    def generate_report(self) -> Dict[str, Any]:
        scan = self.scanner.summarize()
        now = datetime.datetime.now().isoformat()
        framework = scan['framework']
        file_count = scan['file_count']
        config_files = scan.get('config_files', [])
        
        # Adaptive identity and recommendations
        identity = f"Agente Synrax specializzato in {framework}" if framework != 'unknown' else "Agente Synrax generico"
        recommendations = self._get_recommendations(framework)
        
        # Build sanitized report: do NOT include raw contents or full paths
        self.report = {
            'timestamp': now,
            'identity': identity,
            'framework': framework,
            'file_count': file_count,
            'config_files': config_files,
            'config_sensitive_keys': scan.get('config_sensitive_keys', {}),
            'recommendations': recommendations,
            'notice': 'Questo report è sanitizzato: nessun contenuto raw o path completi vengono inclusi.'
        }
        return self.report

    def _get_recommendations(self, framework: str) -> str:
        if framework == 'Django':
            return "Verifica CSRF, usa settings.SECURE_*, aggiorna dipendenze, configura CORS."
        elif framework == 'FastAPI':
            return "Usa HTTPS, rate limiting, valida input, configura CORS, aggiungi security headers."
        elif framework == 'Flask':
            return "Abilita session cookie sicuri, usa Flask-SeaSurf, aggiorna dipendenze, configura CORS."
        elif framework == 'Node.js':
            return "Usa helmet, rate limiting, valida input, aggiorna dipendenze, configura CORS."
        elif framework == 'React':
            return "Sanitizza input, usa CSP, aggiorna dipendenze, limita accesso API."
        elif framework == 'Next.js':
            return "Configura CSP, limita accesso API, aggiorna dipendenze, usa HTTPS."
        else:
            return "Applica best practice di sicurezza generali: valida input, aggiorna dipendenze, usa HTTPS, configura CORS e security headers."
