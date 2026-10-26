"""Persist only per-store retry deadlines, never cookies or credentials."""
import json
import math
import time
from pathlib import Path


class BackoffState:
    def __init__(self, config):
        db = getattr(config, 'db', '')
        self.path = Path(db).with_name('store-backoff.json') if db and Path(db).parent != Path('.') else None
        self.allowed = set(config.domains)
        self.entries = {}
        if self.path:
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                now = time.time()
                for kind in ('access', 'rate'):
                    for domain, deadline in data.get(kind, {}).items():
                        if domain in self.allowed and type(deadline) in (int, float) and math.isfinite(deadline) and now < deadline:
                            self.entries.setdefault(kind, {})[domain] = deadline
            except (OSError, ValueError, TypeError, AttributeError):
                pass

    def restore(self, kind):
        return {domain: time.monotonic() + max(0, deadline - time.time())
                for domain, deadline in self.entries.get(kind, {}).items()}

    def pause(self, kind, domain, seconds):
        if not self.path or domain not in self.allowed:
            return
        self.entries.setdefault(kind, {})[domain] = time.time() + max(seconds, 1)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.entries), encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            pass  # In-memory backoff still applies if persistence is unavailable.
