"""Battle data (based on Red++): moves with the physical/special split, types and the type chart, and base stats,
from data/moves.json, data/types.json and data/pokemon.json."""
import os, json

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
_load = lambda n: json.load(open(os.path.join(DATA, n + '.json')))
_types = _load('types')
TYPES = _types['ids']
TYPECHART = [(TYPES[a], TYPES[d], x) for a, d, x in _types['chart']]
MOVEID, MOVES = {}, {}
for name, m in _load('moves').items():
    MOVEID[name] = m['id']
    MOVES[m['id']] = dict(id=m['id'], eff=m['effect'], pow=m['power'], type=TYPES[m['type']], acc=m['accuracy'],
                          pp=m['pp'], name=m['name'], cat=['PHYSICAL', 'SPECIAL', 'STATUS'].index(m['category']))
_mons = _load('pokemon')
STATS = {n: dict(stats=p['stats'], types=[TYPES[t] for t in p['types']], catch=p['catch'], bexp=p['bexp'],
                 growth=p['growth']) for n, p in _mons.items()}
