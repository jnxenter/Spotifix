"""Lectura de datos de cuentas desde la pantalla de Spotify.

El telefono ya tiene la sesion iniciada, asi que no se usan credenciales ni
APIs privadas: se abre la pagina de cuenta de Spotify y se leen los textos
que muestran el correo, el plan y la fecha de renovacion.

Este modulo solo contiene el parseo (testeable sin dispositivos). La
navegacion por la UI vive en api.py.
"""

import re
import unicodedata
from datetime import date, timedelta

try:
    import xml.etree.ElementTree as _ET
except Exception:  # pragma: no cover
    _ET = None


EMAIL_RE = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')

_ISO_RE = re.compile(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b')
_NUMERIC_RE = re.compile(r'\b(\d{1,2})[\/.\-](\d{1,2})[\/.\-](\d{2,4})\b')
_DAY_MONTH_YEAR_RE = re.compile(
    r'\b(\d{1,2})\s*(?:de\s+)?([A-Za-z]{3,10})\.?\s*(?:de\s+)?(\d{4})\b', re.I)
_MONTH_DAY_YEAR_RE = re.compile(
    r'\b([A-Za-z]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b', re.I)

_MONTHS = {
    'jan': 1, 'january': 1, 'ene': 1, 'enero': 1,
    'feb': 2, 'february': 2, 'febrero': 2,
    'mar': 3, 'march': 3, 'marzo': 3,
    'apr': 4, 'april': 4, 'abr': 4, 'abril': 4,
    'may': 5, 'mayo': 5,
    'jun': 6, 'june': 6, 'junio': 6,
    'jul': 7, 'july': 7, 'julio': 7,
    'aug': 8, 'august': 8, 'ago': 8, 'agosto': 8,
    'sep': 9, 'sept': 9, 'september': 9, 'septiembre': 9, 'setiembre': 9,
    'oct': 10, 'october': 10, 'octubre': 10,
    'nov': 11, 'november': 11, 'noviembre': 11,
    'dec': 12, 'december': 12, 'dic': 12, 'diciembre': 12,
}

RENEWAL_KEYWORDS = (
    'renew', 'renewal', 'next payment', 'next billing', 'payment date',
    'expires', 'expiry', 'expiration', 'ends on', 'end date', 'valid until',
    'vence', 'vencimiento', 'renovacion', 'renueva', 'proximo pago',
    'proximo cobro', 'siguiente pago', 'caduca', 'finaliza', 'valido hasta',
    'hasta el',
    # Texto real de Spotify ES: "Tu proxima factura sera de 12,99 US$ y
    # llegara el 30/11/2026." (se compara sin acentos ni mayusculas).
    'proxima factura', 'siguiente factura', 'factura el', 'factura sera',
    'llegara el', 'llegara la proxima', 'proximo cargo', 'cargo el',
    'se renovara', 'renovara el', 'proxima renovacion', 'proximo vencimiento',
    'termina', 'termina el', 'prueba termina', 'prueba finaliza',
)

FREE_PHRASES = (
    'spotify free', 'free plan', 'plan free', 'plan gratis', 'free tier',
    'plan gratuito', 'cuenta gratis', 'cuenta gratuita', 'cuenta free',
)

PAYMENT_ISSUE_KEYWORDS = (
    'update payment', 'payment failed', 'failed payment', 'problem with your payment',
    'actualiza tu pago', 'pago fallido', 'problema con tu pago', 'revisa tu metodo de pago',
)

_USED_BY_OTHER_KEYWORDS = (
    'being used by another user', 'used by another user',
    'siendo usado por otro usuario', 'usada por otro usuario',
)

_PLAN_CONTEXT_LABELS = (
    'your plan', 'tu plan', 'current plan', 'plan actual',
    'your subscription', 'tu suscripcion', 'subscription', 'suscripcion',
)

_PREMIUM_PLAN_RE = re.compile(
    r'premium\s*(individual|individuale|duo|family|familiar|student|estudiante|trial|prueba)?',
    re.I)


def strip_accents(text):
    if not text:
        return ''
    return ''.join(
        c for c in unicodedata.normalize('NFKD', str(text))
        if not unicodedata.combining(c)
    )


def _norm(text):
    return re.sub(r'\s+', ' ', strip_accents(text or '').lower()).strip()


def extract_texts(xml):
    """Devuelve los textos visibles de un dump de uiautomator, en orden."""
    if not xml:
        return []
    values = []
    if _ET is not None:
        try:
            root = _ET.fromstring(xml)
            for node in root.iter():
                for attr in ('text', 'content-desc'):
                    v = (node.attrib.get(attr) or '').strip()
                    if v:
                        values.append(v)
            return _dedupe(values)
        except Exception:
            pass
    # Fallback: regex sobre el XML crudo si no parsea.
    for m in re.finditer(r'(?:text|content-desc)="([^"]+)"', xml):
        v = m.group(1).strip()
        if v:
            values.append(v)
    return _dedupe(values)


def _dedupe(values):
    seen = set()
    out = []
    for v in values:
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _month_number(name):
    key = _norm(name).strip('. ')
    if key in _MONTHS:
        return _MONTHS[key]
    short = key[:3]
    return _MONTHS.get(short, 0)


def _safe_date(year, month, day):
    try:
        return date(int(year), int(month), int(day))
    except (TypeError, ValueError):
        return None


def extract_dates(text):
    """Lista de (texto_original, date, posicion) encontrados en un texto."""
    if not text:
        return []
    found = []

    for m in _ISO_RE.finditer(text):
        d = _safe_date(m.group(1), m.group(2), m.group(3))
        if d:
            found.append((m.group(0), d, m.start()))

    for m in _NUMERIC_RE.finditer(text):
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        # dd/mm por defecto (LatAm); si el segundo supera 12 es mm/dd.
        if a > 12 and b <= 12:
            day, month = a, b
        elif b > 12 and a <= 12:
            month, day = a, b
        else:
            day, month = a, b
        d = _safe_date(y, month, day)
        if d:
            found.append((m.group(0), d, m.start()))

    for m in _DAY_MONTH_YEAR_RE.finditer(text):
        month = _month_number(m.group(2))
        d = _safe_date(m.group(3), month, m.group(1))
        if d:
            found.append((m.group(0), d, m.start()))

    for m in _MONTH_DAY_YEAR_RE.finditer(text):
        month = _month_number(m.group(1))
        d = _safe_date(m.group(3), month, m.group(2))
        if d:
            found.append((m.group(0), d, m.start()))

    found.sort(key=lambda x: x[2])
    return found


def _canonical_plan(raw):
    n = _norm(raw)
    if 'premium' in n:
        if 'duo' in n:
            return 'Premium Duo'
        if 'family' in n or 'familiar' in n:
            return 'Premium Family'
        if 'student' in n or 'estudiante' in n:
            return 'Premium Student'
        if 'trial' in n or 'prueba' in n:
            return 'Premium Trial'
        if 'individual' in n:
            return 'Premium Individual'
        return 'Premium'
    if 'free' in n or 'gratis' in n or 'gratuito' in n or 'gratuita' in n:
        return 'Free'
    return (raw or '').strip()


def _plan_from_context(texts):
    """Busca la etiqueta 'Your plan' y devuelve el valor que la sigue."""
    for i, text in enumerate(texts):
        label = _norm(text).strip(' :')
        if label in _PLAN_CONTEXT_LABELS:
            for j in range(i + 1, min(i + 4, len(texts))):
                cand = _norm(texts[j])
                if ('premium' in cand or 'free' in cand or 'gratis' in cand
                        or 'gratuito' in cand or 'gratuita' in cand):
                    return texts[j]
    return ''


def _pick_email(texts, fallback_email=''):
    emails = []
    for text in texts:
        for m in EMAIL_RE.finditer(text or ''):
            e = m.group(0)
            if e.lower() not in [x.lower() for x in emails]:
                emails.append(e)
    if not emails:
        return ''
    if fallback_email:
        for e in emails:
            if e.lower() == fallback_email.lower():
                return e
    non_spotify = [e for e in emails if not e.lower().endswith('@spotify.com')]
    return (non_spotify or emails)[0]


def _find_renewal_date(texts, today=None):
    today = today or date.today()
    if not texts:
        return None, ''
    joined = '\n'.join(texts)
    norm_join = strip_accents(joined)

    def _valid(pair):
        d = pair[1]
        return d >= today - timedelta(days=1) and (d - today).days <= 800

    # 1) fecha cerca de una palabra de renovacion (sirve aunque el texto
    #    venga partido en varios nodos).
    low = norm_join.lower()
    for key in RENEWAL_KEYWORDS:
        start = 0
        while True:
            idx = low.find(key, start)
            if idx < 0:
                break
            window = norm_join[idx: idx + 120]
            dates = [p for p in extract_dates(window) if _valid(p)]
            if dates:
                return dates[0][1], dates[0][0]
            start = idx + len(key)

    # 2) linea por linea (por si el orden del dump no es el visual).
    for line in texts:
        nline = _norm(line)
        if any(k in nline for k in RENEWAL_KEYWORDS):
            dates = [p for p in extract_dates(line) if _valid(p)]
            if dates:
                return dates[0][1], dates[0][0]

    # 3) cualquier fecha futura plausible (la pagina de cuenta suele tener
    #    una sola fecha de renovacion).
    dates = [p for p in extract_dates(joined) if _valid(p)]
    if dates:
        best = min(dates, key=lambda p: p[1])
        return best[1], best[0]
    return None, ''


def parse_account_texts(texts, hint_free=False, fallback_email='', account_type_hint=''):
    """Convierte los textos de la pagina de cuenta en datos estructurados."""
    texts = [t.strip() for t in (texts or []) if t and t.strip()]
    joined = '\n'.join(texts)
    norm = _norm(joined)

    email = _pick_email(texts, fallback_email)

    context_plan = _plan_from_context(texts)
    plan = ''
    is_premium = False

    if context_plan:
        plan = _canonical_plan(context_plan)
        is_premium = plan.startswith('Premium')
    elif hint_free:
        # El tab "Premium" dentro de la app solo se muestra a cuentas Free.
        plan = 'Free'
    else:
        m = _PREMIUM_PLAN_RE.search(norm)
        if m:
            plan = _canonical_plan(m.group(0))
            is_premium = True
        elif any(p in norm for p in FREE_PHRASES):
            plan = 'Free'
        else:
            hint = _norm(account_type_hint)
            if 'premium' in hint:
                plan = _canonical_plan(account_type_hint)
                is_premium = True
            elif 'free' in hint or 'gratis' in hint:
                plan = 'Free'

    expires, expires_raw = (None, '')
    if is_premium:
        expires, expires_raw = _find_renewal_date(texts)

    status = 'unknown'
    detail = ''
    if any(k in norm for k in _USED_BY_OTHER_KEYWORDS):
        status = 'in_use'
        detail = 'La cuenta aparece en uso por otro usuario.'
    elif any(k in norm for k in PAYMENT_ISSUE_KEYWORDS):
        status = 'payment_issue'
        detail = 'Spotify pide actualizar el metodo de pago.'
    elif is_premium and expires:
        status = 'ok'
        days = (expires - date.today()).days
        detail = f'Premium, renueva en {days} dia(s).'
    elif is_premium:
        status = 'premium_no_date'
        detail = 'Premium, pero la fecha de renovacion no aparece en la pagina.'
    elif plan == 'Free':
        status = 'free'
        detail = 'Cuenta Free (sin Premium).'
    else:
        status = 'unknown'
        detail = 'No se pudo determinar el plan.'

    return {
        'email': email,
        'plan': plan or '',
        'is_premium': bool(is_premium),
        'expires_on': expires.isoformat() if expires else None,
        'expires_raw': expires_raw or '',
        'status': status,
        'detail': detail,
    }
