import os
import re
from typing import List, Dict, Any

class ProjectScanner:
    """
    Scans the project directory, detects frameworks, and extracts key info for security and knowledge analysis.
    """
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.files: List[str] = []
        self.framework: str = "unknown"
        self.summary: Dict[str, Any] = {}

    def scan_files(self) -> List[str]:
        """Recursively scan project files, excluding sensitive dirs/files."""
        self.files = []
        exclude_dirs = {'.git', '.hg', '.svn', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env', 'logs', 'dist', 'build', '.mypy_cache', '.pytest_cache'}
        exclude_files = {'.env', '.env.local', '.env.prod', '.env.dev', 'id_rsa', 'id_rsa.pub', 'id_ed25519', 'id_ed25519.pub'}
        allowed_exts = ('.py', '.js', '.ts', '.json', '.yml', '.yaml', '.toml', '.md', '.ini', '.cfg')

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Prune excluded directories in-place
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

            for f in filenames:
                if f in exclude_files:
                    continue
                if not f.lower().endswith(allowed_exts):
                    continue
                full_path = os.path.join(dirpath, f)
                self.files.append(full_path)
        return self.files

    def detect_framework(self) -> str:
        """Detect main framework used in the project."""
        framework_patterns = {
            'Django': r"django[=><]",
            'FastAPI': r"fastapi[=><]",
            'Flask': r"flask[=><]",
            'Node.js': r"express|koa|hapi",
            'React': r"react",
            'Next.js': r"next",
        }
        for file in self.files:
            try:
                with open(file, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for fw, pattern in framework_patterns.items():
                        if re.search(pattern, content, re.IGNORECASE):
                            self.framework = fw
                            return fw
            except Exception:
                continue
        return self.framework

    def extract_config(self) -> Dict[str, Any]:
        """Extract non-sensitive config metadata only (no raw content)."""
        config_summary: Dict[str, Any] = {}
        sensitive_keys = [
            'secret', 'password', 'passwd', 'token', 'apikey', 'api_key', 'private_key', 'access_key', 'secret_key',
            'dsn', 'connection', 'conn', 'uri', 'url', 'endpoint', 'auth', 'bearer', 'jwt', 'key'
        ]
        key_pattern = re.compile(r"^\s*([A-Za-z0-9_\-.]+)\s*[:=]", re.IGNORECASE)

        for file in self.files:
            lower = file.lower()
            if not any(x in lower for x in ['config', 'settings', 'pyproject', 'package.json', 'requirements', 'docker', 'compose', 'appsettings', 'application']):
                continue
            try:
                with open(file, encoding='utf-8', errors='ignore') as f:
                    found_keys = set()
                    for raw in f:
                        line = raw.strip()
                        # Only collect key names; never include values
                        m = key_pattern.match(line)
                        if m:
                            key = m.group(1).lower()
                            # Normalize keys like "environment:" or similar won't be included unless sensitive
                            if any(sk in key for sk in sensitive_keys):
                                found_keys.add(key)
                    if found_keys:
                        # Store only filename (basename) and the list of sensitive key names
                        config_summary[os.path.basename(file)] = sorted(found_keys)
            except Exception:
                continue
        return config_summary

    def summarize(self) -> Dict[str, Any]:
        """Produce a sanitized summary with no raw file paths or contents."""
        self.scan_files()
        fw = self.detect_framework()
        config_meta = self.extract_config()
        # Only expose minimal, non-identifying metadata
        self.summary = {
            'framework': fw,
            'file_count': len(self.files),
            'config_files': list(config_meta.keys()),  # basenames only
            'config_sensitive_keys': config_meta,      # filename -> [keys]
        }
        return self.summary
