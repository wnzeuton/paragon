import re
import unicodedata

# ---------------------------------------------------------------------------
# Phrase-level substitutions — applied first (in order) to the lowercased string.
# Handles multi-token catalog abbreviations and common customer acronyms.
# ---------------------------------------------------------------------------
_PHRASE_SUBS = [
    # Strip "in"/"inch" unit suffix directly attached to a number (e.g. "5/8in" → "5/8")
    (r'(\d)(?:in|inch)\b',           r'\1'),
    # Material grades — most specific first so "18-8 ss" isn't caught by generic "ss"
    (r'\b18-8\s+ss\b',               'eighteen eight stainless steel'),
    (r'\b316\s+ss\b',                '316 stainless steel'),
    (r'\ba2\s+ss\b',                 'a2 stainless steel'),
    # Finish combos
    (r'\bmech(?:anical)?\s+z(?:inc|n|c)\b', 'mechanical zinc'),
    (r'\byel(?:low)?\s+z(?:inc|n|c)\b',     'yellow zinc'),
    (r'\bhot\s*[\-\s]?dip\s+galv(?:anized)?\b', 'hot dip galvanized'),
    # Customer-side full acronyms → expand before anything else
    (r'\bshcs\b',  'socket head cap screw'),
    (r'\bhhb\b',   'hex head bolt'),
    (r'\bfhcs\b',  'flat head cap screw'),
    (r'\bbhcs\b',  'button head cap screw'),
    (r'\bbscs\b',  'button socket cap screw'),
    (r'\bphs\b',   'phillips head screw'),
    # Catalog multi-word abbreviations
    (r'\bhx\s+cap\s+scr(?:ew)?\b',                   'hex cap screw'),
    (r'\bsoc(?:ket)?\s+head\s+cap\s+scr(?:ew)?\b',   'socket head cap screw'),
    (r'\bbtn\s+soc(?:ket)?\s+cap\s+scr(?:ew)?\b',    'button socket cap screw'),
    (r'\bphil(?:lips)?\s+pan\b',                      'phillips pan'),
    (r'\bflat\s+wshr\b',                              'flat washer'),
    (r'\block\s+wshr\b',                              'lock washer'),
    (r'\bhx\s+nut\b',                                 'hex nut'),
    (r'\bfull\s+thr(?:ea)?d\b',                       'full thread'),
]

_PHRASE_SUBS_COMPILED = [(re.compile(p, re.IGNORECASE), r) for p, r in _PHRASE_SUBS]

# ---------------------------------------------------------------------------
# Token-level substitutions — applied token-by-token after splitting.
# Handles remaining single-token abbreviations not covered by phrase subs.
# ---------------------------------------------------------------------------
_TOKEN_SUBS = {
    'hx':    'hex',
    'soc':   'socket',
    'scr':   'screw',
    'btn':   'button',
    'phil':  'phillips',
    'mach':  'machine',
    'wshr':  'washer',
    'hdg':   'hot dip galvanized',
    'zn':    'zinc',
    'zc':    'zinc',
    'mz':    'mechanical zinc',
    'yz':    'yellow zinc',
    'yel':   'yellow',
    'bo':    'black oxide',
    'pl':    'plain',
    'pln':   'plain',
    'ss':    'stainless steel',
    'mech':  'mechanical',
    # standalone customer abbreviations not already phrase-expanded
    'hn':    'hex nut',
    'fw':    'flat washer',
    'lw':    'lock washer',
    'hd':    'head',
    'cap':   'cap',
}

_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
    'for', 'of', 'with', 'is', 'it', 'its', 'by', 'as', 'be', 'are',
    # dimensional words customers use that never appear in catalog descriptions
    'inch', 'inches',
}

# ---------------------------------------------------------------------------
# Attribute-extraction patterns — run on the RAW (original case) description.
# ---------------------------------------------------------------------------

# Thread: metric M8, M8-1.25 | imperial 3/8-16 | numbered #10-24 | bare fraction 1/2
# Bare fraction (\d+/\d+) is last so fully-specified 3/8-16 takes priority.
_THREAD_PAT = re.compile(
    r'(M\d+(?:-\d+(?:\.\d+)?)?)'   # M8 or M8-1.25
    r'|(\d+/\d+-\d+)'               # 3/8-16
    r'|(#\d+-\d+)'                  # #10-24
    r'|(\d+/\d+)',                   # 1/2 (bare fraction, pitch implied)
    re.IGNORECASE,
)

# Length: token after literal " X " (catalog) or standalone metric/imperial length
_LENGTH_AFTER_X = re.compile(
    r'\bx\s+(\d+(?:[-/]\d+)*(?:mm|ft|")?)',
    re.IGNORECASE,
)
_LENGTH_FREEFORM = re.compile(
    r'(\d+(?:[-/]\d+)?)\s*(?:foot|feet|ft\b)',
    re.IGNORECASE,
)

# Fastener type — longest-match, applied in order
_TYPE_PATTERNS = [
    (re.compile(r'\bphillips\s+pan\s+machine\s+screw\b', re.IGNORECASE),       'phillips pan machine screw'),
    (re.compile(r'\bphil(?:lips)?\s+pan\s+mach(?:ine)?\s+scr(?:ew)?\b', re.IGNORECASE), 'phillips pan machine screw'),
    (re.compile(r'\bbutton\s+socket\s+cap\s+screw\b', re.IGNORECASE),          'button socket cap screw'),
    (re.compile(r'\bbtn\s+soc(?:ket)?\s+cap\s+scr(?:ew)?\b', re.IGNORECASE),  'button socket cap screw'),
    (re.compile(r'\bbscs\b', re.IGNORECASE),                                   'button socket cap screw'),
    (re.compile(r'\bsocket\s+head\s+cap\s+screw\b', re.IGNORECASE),            'socket head cap screw'),
    (re.compile(r'\bsoc(?:ket)?\s+head\s+cap\s+scr(?:ew)?\b', re.IGNORECASE), 'socket head cap screw'),
    (re.compile(r'\bshcs\b', re.IGNORECASE),                                   'socket head cap screw'),
    (re.compile(r'\bhex(?:agon(?:al)?)?\s+cap\s+screw\b', re.IGNORECASE),      'hex cap screw'),
    (re.compile(r'\bhx\s+cap\s+scr(?:ew)?\b', re.IGNORECASE),                 'hex cap screw'),
    (re.compile(r'\bhex\s+head\s+bolt\b', re.IGNORECASE),                      'hex cap screw'),
    (re.compile(r'\bhhb\b', re.IGNORECASE),                                    'hex cap screw'),
    (re.compile(r'\blag\s+scr(?:ew)?\b', re.IGNORECASE),                       'lag screw'),
    (re.compile(r'\bthreaded\s+rod\b', re.IGNORECASE),                         'threaded rod'),
    (re.compile(r'\btap\s+bolt\b', re.IGNORECASE),                             'tap bolt'),
    (re.compile(r'\bflat\s+wash(?:er)?\b', re.IGNORECASE),                     'flat washer'),
    (re.compile(r'\bflat\s+wshr\b', re.IGNORECASE),                            'flat washer'),
    (re.compile(r'\block\s+wash(?:er)?\b', re.IGNORECASE),                     'lock washer'),
    (re.compile(r'\block\s+wshr\b', re.IGNORECASE),                            'lock washer'),
    (re.compile(r'\bhex\s+nut\b', re.IGNORECASE),                              'hex nut'),
    (re.compile(r'\bhx\s+nut\b', re.IGNORECASE),                               'hex nut'),
    (re.compile(r'\bhn\b', re.IGNORECASE),                                     'hex nut'),
]

_MATERIAL_PATTERNS = [
    (re.compile(r'\b18-8\s+(?:ss|stainless(?:\s+steel)?)\b', re.IGNORECASE),   '18-8 stainless steel'),
    (re.compile(r'\beighteen\s+eight\s+stainless\s+steel\b', re.IGNORECASE),   '18-8 stainless steel'),
    (re.compile(r'\b316\s+(?:ss|stainless(?:\s+steel)?)\b', re.IGNORECASE),    '316 stainless steel'),
    (re.compile(r'\ba2\s+(?:ss|stainless(?:\s+steel)?)\b', re.IGNORECASE),     'a2 stainless steel'),
    (re.compile(r'\bstainless(?:\s+steel)?\b', re.IGNORECASE),                 'stainless steel'),
    (re.compile(r'\bbrass\b', re.IGNORECASE),                                  'brass'),
    (re.compile(r'\balloy\b', re.IGNORECASE),                                  'alloy'),
    (re.compile(r'\bsteel\b', re.IGNORECASE),                                  'steel'),
]

_FINISH_PATTERNS = [
    (re.compile(r'\bhot\s*[\-\s]?dip\s+galv(?:anized)?\b', re.IGNORECASE),    'hot dip galvanized'),
    (re.compile(r'\bhdg\b', re.IGNORECASE),                                    'hot dip galvanized'),
    (re.compile(r'\bmech(?:anical)?\s+zinc\b', re.IGNORECASE),                 'mechanical zinc'),
    (re.compile(r'\bmech(?:anical)?\s+zn\b', re.IGNORECASE),                   'mechanical zinc'),
    (re.compile(r'\bmz\b', re.IGNORECASE),                                     'mechanical zinc'),
    (re.compile(r'\byellow\s+zinc\b', re.IGNORECASE),                          'yellow zinc'),
    (re.compile(r'\byel(?:low)?\s+zn\b', re.IGNORECASE),                       'yellow zinc'),
    (re.compile(r'\byz\b', re.IGNORECASE),                                     'yellow zinc'),
    (re.compile(r'\byel(?:low)?\s+z(?:inc|c)\b', re.IGNORECASE),              'yellow zinc'),
    (re.compile(r'\bblack\s+oxide\b', re.IGNORECASE),                          'black oxide'),
    (re.compile(r'\bbo\b', re.IGNORECASE),                                     'black oxide'),
    (re.compile(r'\bz(?:inc|n|c)\b', re.IGNORECASE),                           'zinc'),
    (re.compile(r'\bplain\b', re.IGNORECASE),                                  'plain'),
    (re.compile(r'\bpl(?:n)?\b', re.IGNORECASE),                               'plain'),
]

# Tokens that look like thread sizes or dimensions — skip token-level sub
_NUMERIC_PAT = re.compile(r'^[#\d]')
_THREAD_TOKEN_PAT = re.compile(r'^m\d', re.IGNORECASE)


def normalize(text: str) -> str:
    """Normalize text: expand abbreviations (phrase + token level), lowercase, clean."""
    text = unicodedata.normalize('NFKD', text)
    text = text.lower()

    # Phrase-level substitutions
    for pattern, replacement in _PHRASE_SUBS_COMPILED:
        text = re.sub(pattern, replacement, text)

    # Remove characters that aren't alphanumeric, space, or fastener-relevant punctuation
    text = re.sub(r'[^\w\s\-/#.]', ' ', text)

    # Token-level substitutions; drop stopwords
    tokens = text.split()
    expanded = []
    for tok in tokens:
        if tok in _STOPWORDS:
            continue
        if _NUMERIC_PAT.match(tok) or _THREAD_TOKEN_PAT.match(tok):
            expanded.append(tok)
        else:
            expanded.append(_TOKEN_SUBS.get(tok, tok))
    return ' '.join(expanded)


def tokenize(text: str) -> list:
    """Split normalized text into meaningful tokens, dropping stopwords."""
    return [t for t in text.lower().split() if t not in _STOPWORDS and len(t) >= 2]


def extract_attributes(raw_desc: str) -> dict:
    """
    Parse structured attributes from a raw fastener description or user query.
    Returns a dict with keys: thread, length, type, material, finish.
    Values are None when not found.
    """
    attrs = {'thread': None, 'length': None, 'type': None, 'material': None, 'finish': None}

    # Thread
    m = _THREAD_PAT.search(raw_desc)
    if m:
        attrs['thread'] = m.group(0).lower()

    # Length — "X <value>" format first, then freeform "6 foot" style
    m = _LENGTH_AFTER_X.search(raw_desc)
    if m:
        attrs['length'] = m.group(1).lower().replace('"', 'in').replace(' ', '')
    else:
        m = _LENGTH_FREEFORM.search(raw_desc)
        if m:
            attrs['length'] = m.group(1).lower() + 'ft'

    # Fastener type — longest match wins
    for pattern, type_name in _TYPE_PATTERNS:
        if pattern.search(raw_desc):
            attrs['type'] = type_name
            break

    # Material
    for pattern, mat_name in _MATERIAL_PATTERNS:
        if pattern.search(raw_desc):
            attrs['material'] = mat_name
            break

    # Finish
    for pattern, finish_name in _FINISH_PATTERNS:
        if pattern.search(raw_desc):
            attrs['finish'] = finish_name
            break

    return attrs
