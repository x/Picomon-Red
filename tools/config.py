"""Game config (config/*.json): the species in the cart with their evolutions and learnsets, every trainer's team, and
the wild tables. check(B) validates it against the extracted data once the build has read pokered + Red++."""
import os, json

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config')
POKEMON, TRAINERS, WILD = (json.load(open(os.path.join(DIR, f + '.json'))) for f in ('pokemon', 'trainers', 'wild'))
STARTERS = ['BULBASAUR', 'CHARMANDER', 'SQUIRTLE']


def teams():
    """(where, team) for every team in trainers.json"""
    t = TRAINERS
    return ([('leaders/' + k, v) for k, v in t['leaders'].items()] + [('champion/' + k, v) for k, v in t['champion'].items()]
            + [('rival/%d' % i, v) for i, v in enumerate(t['rival'])] + [('trainers/' + k, v) for k, v in t['trainers'].items()])


def fought():
    """species seen in battle (they need a front pic)"""
    return {sp for _, t in teams() for _, sp in t} | {sp for w in WILD.values() for _, sp in w['mons']}


def ownable():
    """species the player can own (they need a back pic): starters, wild species and what they evolve into"""
    own = set(STARTERS) | {sp for w in WILD.values() for _, sp in w['mons']}
    while True:
        more = {POKEMON[o]['evolves'][0] for o in own if o in POKEMON and 'evolves' in POKEMON[o]} - own
        if not more:
            return own
        own |= more


def check(B):
    import rpp
    err = []
    for n, p in POKEMON.items():
        if n not in B.DEX:
            err.append('pokemon.json: %s has no entry in data/pokemon.json (its stats, types and palette)' % n)
            continue
        if not p.get('learnset'):
            err.append('pokemon.json: %s needs a learnset' % n)
        for lv, m in p.get('learnset', []):
            if m not in rpp.MOVEID:
                err.append('pokemon.json: %s learns %s, which has no entry in data/moves.json' % (n, m))
            if not 1 <= lv <= 100:
                err.append('pokemon.json: %s learns %s at level %s' % (n, m, lv))
        if 'evolves' in p:
            to, lv = p['evolves']
            if to not in POKEMON:
                err.append('pokemon.json: %s evolves into %s, which is not in pokemon.json' % (n, to))
            if not 2 <= lv <= 100:
                err.append('pokemon.json: %s evolves at level %s' % (n, lv))
    for n in POKEMON:  # evolution loops
        seen, s = set(), n
        while s in POKEMON and 'evolves' in POKEMON[s] and s not in seen:
            seen.add(s)
            s = POKEMON[s]['evolves'][0]
        if s in seen:
            err.append('pokemon.json: evolution loop through %s' % n)
    for where, t in teams():
        if not 1 <= len(t) <= 6:
            err.append('trainers.json %s: %d pokemon (1-6)' % (where, len(t)))
        for lv, sp in t:
            if sp not in POKEMON:
                err.append('trainers.json %s: %s is not in pokemon.json' % (where, sp))
            if not 1 <= lv <= 100:
                err.append('trainers.json %s: level %s' % (where, lv))
    for m, w in WILD.items():
        if len(w['mons']) != 10 or not 1 <= w['rate'] <= 255:
            err.append('wild.json %s: needs 10 slots and a rate of 1-255' % m)
        for lv, sp in w['mons']:
            if sp not in POKEMON:
                err.append('wild.json %s: %s is not in pokemon.json' % (m, sp))
    for s in STARTERS:
        if s not in POKEMON:
            err.append('pokemon.json: starter %s missing' % s)
    if err:
        raise SystemExit('config errors:\n  ' + '\n  '.join(err))
    unused = set(POKEMON) - fought() - ownable()
    if unused:
        print('config: never seen or owned (wasted space):', ' '.join(sorted(unused)))
