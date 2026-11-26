#!/usr/bin/env python3
"""Draw the inline SVG figures for src/content/work/stacked-guardrails.md.

Data: stacked-guardrails.json next to this file (copied from the study's result files).
The figures are written between <!-- fig:NAME --> and <!-- /fig:NAME --> markers in the
Markdown file, so the page stays one file. Colours are CSS variables (.fig in global.css),
so the charts follow the site's light/dark theme. Output has no blank lines: a blank line
ends a Markdown HTML block.

Usage: python3 tools/figures/stacked-guardrails.py
"""
import json, math, re
from pathlib import Path

HERE = Path(__file__).parent
MD = HERE / '../../src/content/work/stacked-guardrails.md'
D = json.loads((HERE / 'stacked-guardrails.json').read_text())

NAME = {
    'deepset': 'deepset injection', 'jackhhao': 'jackhhao jailbreak', 'protectai': 'ProtectAI v2',
    'piguard': 'PIGuard', 'promptguard2_86m': 'Prompt Guard 2 86M', 'promptguard2_22m': 'Prompt Guard 2 22M',
    'qwen3guard': 'Qwen3Guard 0.6B', 'llamaguard3_1b': 'Llama Guard 3 1B', 'shieldgemma': 'ShieldGemma 2B',
    'granite': 'Granite Guardian 3.1 2B', 'perplexity': 'GPT-2 perplexity',
}


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def pct(x):
    return f'{x * 100:.0f}%' if abs(x * 100 - round(x * 100)) < 0.05 else f'{x * 100:.1f}%'


# ---------- Figure 1: effective layers per pair ----------
def layers():
    W, L, R = 560, 14, 546
    lo, hi = 1.0, 3.0
    X = lambda v: L + (v - lo) / (hi - lo) * (R - L)
    rows = [
        ('inj+inj', 'Two injection classifiers', 'same'),
        ('harm+harm', 'Two harm guards', 'same'),
        ('harm+inj', 'One harm guard + one injection classifier', 'mixed'),
        ('ppl', 'Either kind + perplexity filter', 'ppl'),
    ]
    top, rh = 34, 70
    H = top + rh * len(rows) + 30
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="fig-layers-t" class="fig-layers">',
         '<title id="fig-layers-t">Effective layers for all 55 pairs of the 11 guards, grouped by the kinds of guard in the pair</title>']
    y0, y1 = top - 8, top + rh * len(rows) - 6
    for v in (1.0, 1.5, 2.0, 2.5, 3.0):
        o.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{y0}" y2="{y1}" class="grid"/>')
    o.append(f'<line x1="{X(2):.1f}" x2="{X(2):.1f}" y1="{y0 - 6}" y2="{y1}" class="ref"/>')
    o.append(f'<text x="{X(2) + 6:.1f}" y="{y0 - 10}" class="note">2.0 = two independent guards</text>')
    for i, (k, label, cls) in enumerate(rows):
        ps = [p for p in D['pairs'] if (p['kinds'] == k if k != 'ppl' else 'ppl' in p['kinds'])]
        yl = top + i * rh + 10
        yc = yl + 24
        placed = []
        for p in sorted(ps, key=lambda p: p['n_eff']):
            x = X(p['n_eff'])
            # Simple beeswarm: stack dots that would overlap, alternating above and below the line.
            dy, step = 0, 0
            while any(abs(x - px) < 9 and abs(dy - pdy) < 9 for px, pdy in placed):
                step += 1
                dy = ((step + 1) // 2) * 8 * (1 if step % 2 else -1)
            placed.append((x, dy))
            tip = f"{NAME[p['a']]} + {NAME[p['b']]}: {p['n_eff']:.2f} effective layers; catches {pct(p['tpr'])}, flags {pct(p['fpr'])} of benign prompts"
            o.append(f'<circle cx="{x:.1f}" cy="{yc + dy}" r="5" class="dot {cls}"><title>{esc(tip)}</title></circle>')
        med = sorted(p['n_eff'] for p in ps)
        m = (med[len(med) // 2] + med[(len(med) - 1) // 2]) / 2
        o.append(f'<line x1="{X(m):.1f}" x2="{X(m):.1f}" y1="{yc - 15}" y2="{yc + 15}" class="median"/>')
        o.append(f'<text x="{L}" y="{yl}" class="label">{esc(label)} <tspan class="note">· {len(ps)} pairs, median {m:.2f}</tspan></text>')
    ya = top + rh * len(rows) + 10
    for v in (1.0, 1.5, 2.0, 2.5, 3.0):
        anchor = 'start' if v == lo else 'end' if v == hi else 'middle'
        o.append(f'<text x="{X(v):.1f}" y="{ya}" class="tick" text-anchor="{anchor}">{v:.1f}</text>')
    o.append(f'<text x="{(L + R) / 2:.1f}" y="{ya + 18}" class="note" text-anchor="middle">effective layers</text>')
    o.append('</svg>')
    return ('<figure class="fig">' + ''.join(o) +
            '<figcaption>Each dot is one pair of guards. One layer means the second guard catches nothing the first one missed; '
            'two means the pair behaves like two independent guards; above two, the guards miss different attacks. '
            'The bar in each row is the median. Hover a dot for the pair, its catch rate and its false-positive rate.</figcaption></figure>')


# ---------- Figure 2: adaptive attack success against query budget ----------
def attack():
    names = {'open': ('PIGuard', 'Qwen3Guard 0.6B', 'PIGuard + Qwen3Guard', 54),
             'meta': ('Prompt Guard 2 86M', 'Llama Guard 3 1B', 'Llama Guard 3 + Prompt Guard 2', 30)}
    W, H, L, R, T, B = 320, 214, 40, 308, 30, 182
    X = lambda q: L + math.log10(q) / math.log10(300) * (R - L)
    Y = lambda a: B - a * (B - T)
    panels = []
    for s in ('open', 'meta'):
        inj, harm, pair, n = names[s]
        for muts, mlabel in (('full', 'with filler'), ('nopad', 'without filler')):
            c = D['attack'][s][muts]
            o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(pair)}, attacker {mlabel}: share of {n} requests that got past, by number of queries">']
            o.append(f'<text x="{L - 34}" y="14" class="label">{esc(pair)} <tspan class="note">· {mlabel}</tspan></text>')
            for a in (0, 0.5, 1):
                o.append(f'<line x1="{L}" x2="{R}" y1="{Y(a):.1f}" y2="{Y(a):.1f}" class="grid"/>')
                o.append(f'<text x="{L - 6}" y="{Y(a) + 4:.1f}" class="tick" text-anchor="end">{int(a * 100)}%</text>')
            for q in (1, 10, 100, 300):
                o.append(f'<text x="{X(q):.1f}" y="{B + 16}" class="tick" text-anchor="middle">{q}</text>')
            o.append(f'<text x="{(L + R) / 2:.1f}" y="{B + 30}" class="note" text-anchor="middle">queries to the guards (log scale)</text>')
            for role, cls, label in (('inj', 's1', inj), ('harm', 's2', harm), ('pair', 'pair', pair)):
                pts = c[role]
                d = ' '.join(f'{X(q):.1f},{Y(a):.1f}' for q, a in pts)
                o.append(f'<polyline points="{d}" class="line {cls}"/>')
                for q, a in pts:
                    tip = f'{label}, {mlabel}: {pct(a)} of {n} requests through within {q} queries'
                    o.append(f'<circle cx="{X(q):.1f}" cy="{Y(a):.1f}" r="7" class="hit"><title>{esc(tip)}</title></circle>')
            o.append('</svg>')
            panels.append(''.join(o))
    legend = ('<div class="fig-legend" aria-hidden="true"><span><i class="s1"></i>Injection classifier alone</span>'
              '<span><i class="s2"></i>Harm guard alone</span><span><i class="pair"></i>Both, stacked</span></div>')
    return ('<figure class="fig">' + legend + '<div class="fig-grid">' + ''.join(panels) + '</div>'
            '<figcaption>Share of harmful requests the attacker got past each target, by query budget (up to 300). '
            'Top: 54 requests against PIGuard and Qwen3Guard. Bottom: 30 requests against Meta’s Llama Guard 3 1B and Prompt Guard 2 86M. '
            'With filler, the stacked pair falls almost as fast as its stronger guard alone.</figcaption></figure>')


FIGS = {'layers': layers, 'attack': attack}
text = MD.read_text()
for name, fn in FIGS.items():
    svg = fn()
    assert '\n\n' not in svg
    pat = re.compile(rf'(<!-- fig:{name} -->)\n.*?(<!-- /fig:{name} -->)', re.S)
    assert pat.search(text), f'marker for {name} missing'
    text = pat.sub(lambda m: m.group(1) + '\n' + svg + '\n' + m.group(2), text)
MD.write_text(text)
print('updated', MD.resolve())
