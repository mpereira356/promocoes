"""Rotulos curtos para a interface; detalhes tecnicos continuam no diagnostico."""
from .models import normalize


def short_reason(text):
    plain = normalize(text)
    if 'bloque' in plain or 'recusou acesso' in plain: return 'acesso bloqueado pela loja'
    if 'captcha' in plain: return 'a loja pediu verificação de acesso'
    if 'robots' in plain: return 'consulta indisponível nesta loja'
    if 'tempo limite' in plain or 'demorou' in plain: return 'a loja demorou para responder'
    if 'limite' in plain or 'limitou' in plain or 'limitado' in plain: return 'consultas temporariamente limitadas'
    if 'conexao' in plain or 'rede' in plain: return 'falha de conexão'
    if 'servidor' in plain: return 'loja temporariamente indisponível'
    return text.split('\n', 1)[0].split('. ', 1)[0][:130].rstrip('.')


def summarize_notices(notices):
    missing, limited, other, regional = [], [], [], []
    for text in notices:
        plain = normalize(text)
        name, separator, body = text.partition(':')
        if 'precos regionais ainda nao disponiveis' in plain or 'leitura regional de precos ainda nao disponivel' in plain:
            regional.append(name)
        elif 'nao aplicavel' in plain:
            continue
        if 'modelo solicitado nao encontrado' in plain:
            missing.append(name)
        elif 'limite da busca externa' in plain or 'external_search_limited' in plain:
            limited.append(name)
        elif 'a descoberta falhou' in plain:
            continue  # O motivo da mesma loja e apresentado no aviso principal.
        elif 'cache' in plain or 'recuperado' in plain or 'reutilizados' in plain:
            other.append('Links salvos reaproveitados; preços consultados novamente.')
        else:
            other.append(name + ': ' + short_reason(body.strip()) + '.' if separator else short_reason(text))
    if missing: other.append('Sem resultado nesta consulta: ' + ', '.join(dict.fromkeys(missing)) + '.')
    if limited: other.append('Busca limitada: ' + ', '.join(dict.fromkeys(limited)) + '.')
    if regional:
        names = set(regional)
        # The final summary explains the common regional limitation once.
        other = [text for text in other if not text.startswith('Busca limitada: ')] + (
            ['Busca limitada: ' + ', '.join(dict.fromkeys(n for n in limited if n not in names)) + '.']
            if any(n not in names for n in limited) else [])
        other.append('Preços regionais pendentes: ' + ', '.join(dict.fromkeys(regional)) + '.')
    return list(dict.fromkeys(other))
