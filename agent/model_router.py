"""Small policy layer selecting a model backend without giving models direct OS access."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ModelRoute:
    backend: str
    reason: str
    requires_network: bool=False

def choose(task: str, *, local_available=True, online_enabled=False, vision=False) -> ModelRoute:
    q=' '.join(str(task).lower().split())
    if vision: return ModelRoute('vision-local' if local_available else 'vision-optional','Screen understanding requested.',False)
    if any(x in q for x in ('calculate','pc health','system specs','recent files','running apps')):
        return ModelRoute('deterministic','High-confidence local tool task.',False)
    if local_available: return ModelRoute('local-llm','General reasoning can stay local.',False)
    if online_enabled: return ModelRoute('online-knowledge','Local model unavailable and online knowledge is enabled.',True)
    return ModelRoute('fallback','No model backend available.',False)
