#!/usr/bin/env python3
"""Gera o painel SVG e seu equivalente textual a partir da API pública do GitHub.

Python 3.10+, somente biblioteca padrão. Não acessa repositórios privados.
Uso: python scripts/atualizar_perfil.py [--snapshot arquivo.json]
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = 'albsondev'
COLORS = ['#79e6ce', '#9daeff', '#c0a4ff', '#f2cd88', '#f39fa9', '#87cdf0', '#a8d89d', '#d4bddf']


def api(path):
    headers = {'User-Agent': 'albsondev-profile', 'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    with urlopen(Request('https://api.github.com/' + path, headers=headers), timeout=30) as response:
        return json.load(response)


def collect():
    repos = []
    page = 1
    while True:
        batch = api(f'users/{USER}/repos?type=owner&per_page=100&page={page}')
        if not isinstance(batch, list):
            raise ValueError('A API não retornou uma lista de repositórios.')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return {
        'username': USER,
        'consulted_at': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        'repositories': [{key: r.get(key) for key in
                          ('name', 'fork', 'private', 'language', 'stargazers_count')} for r in repos]
    }


def summarize(data):
    repos = [r for r in data['repositories'] if not r.get('private')]
    own = [r for r in repos if not r['fork']]
    langs = Counter(r['language'] for r in own if r.get('language'))
    langs = sorted(langs.items(), key=lambda item: (-item[1], item[0]))
    return repos, own, langs, sum(r['stargazers_count'] for r in own)


def text(x, y, label, size=16, fill='#ecf2fa', extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" {extra}>{escape(str(label))}</text>'


def svg(data):
    repos, own, langs, stars = summarize(data)
    date = datetime.strptime(data['consulted_at'], '%Y-%m-%d').strftime('%d/%m/%Y')
    shown = langs[:8]
    if len(langs) > 8:
        shown = langs[:7] + [('Outras', sum(n for _, n in langs[7:]))]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="510" viewBox="0 0 1000 510" role="img" aria-labelledby="title desc">',
             '<title id="title">GitHub em ritmo — André Albson</title>',
             '<desc id="desc">Estatísticas públicas. Barras representam quantidades de repositórios sem fork por linguagem principal. A luz móvel é decorativa.</desc>',
             '<defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="0.7" fill="#253247"/></pattern></defs>',
             '<style>text{font-family:Arial,Helvetica,sans-serif}.mono{font-family:monospace}.scan{animation:scan 9s linear infinite}@keyframes scan{from{transform:translateX(0)}to{transform:translateX(866px)}}@media(prefers-reduced-motion:reduce){.scan{animation:none;display:none}}</style>',
             '<rect x="1" y="1" width="998" height="508" rx="20" fill="#101923" stroke="#2a394b"/>',
             '<rect x="20" y="20" width="960" height="470" fill="url(#grid)" opacity="0.45"/>',
             text(38, 40, '02 / CÓDIGO EM RITMO', 12, '#79e6ce', 'letter-spacing="2" class="mono"'),
             text(962, 40, 'DADOS PÚBLICOS', 11, '#92a1b7', 'text-anchor="end" letter-spacing="2"')]
    metrics = [(len(repos), 'REPOSITÓRIOS'), (len(own), 'SEM FORK'), (len(repos)-len(own), 'FORKS'), (stars, 'ESTRELAS · SEM FORK')]
    for i, (n, label) in enumerate(metrics):
        x = 38 + i*245
        parts += [text(x, 107, n, 44, '#ecf2fa', 'font-weight="700"'), text(x, 134, label, 11, '#92a1b7', 'letter-spacing="1.3"')]
    parts += ['<path d="M38 160H962" stroke="#2a394b"/>', text(38, 190, 'Cada linguagem, uma voz.', 21, '#ecf2fa', 'font-weight="700"'), text(38, 215, 'Repositórios sem fork, agrupados pela linguagem principal.', 14, '#92a1b7')]
    max_n = max((n for _, n in shown), default=1)
    for i, (lang, count) in enumerate(shown):
        x = 72 + i*116
        height = count/max_n*140
        parts.append(f'<rect x="{x}" y="245" width="42" height="150" rx="5" fill="#1a2837"/>')
        parts.append(f'<rect x="{x}" y="{395-height:.2f}" width="42" height="{height:.2f}" rx="5" fill="{COLORS[i]}"/>')
        for y in range(251, 393, 8):
            parts.append(f'<path d="M{x} {y}h42" stroke="#101923" stroke-width="2"/>')
        parts += [text(x+21, 238, count, 16, COLORS[i], 'text-anchor="middle" font-weight="700"'), text(x+21, 422, lang, 13, '#c5cfdd', 'text-anchor="middle"')]
    parts += ['<rect class="scan" x="48" y="245" width="2" height="150" fill="#ffffff" opacity="0.15"/>',
              '<path d="M38 445H962" stroke="#2a394b"/>',
              text(38, 475, 'DADOS REAIS. UMA ASSINATURA PESSOAL.', 10, '#79e6ce', 'letter-spacing="1.5" class="mono"'),
              text(962, 475, f'Consulta: {date} · UTC', 12, '#92a1b7', 'text-anchor="end"'), '</svg>']
    return '\n'.join(parts) + '\n'


def update(data):
    if data['username'] != USER:
        raise ValueError('Snapshot de outro usuário.')
    repos, own, langs, stars = summarize(data)
    date = datetime.strptime(data['consulted_at'], '%Y-%m-%d').strftime('%d/%m/%Y')
    unknown = len(own) - sum(n for _, n in langs)
    summary = f'**{len(repos)} repositórios públicos · {len(own)} sem fork · {len(repos)-len(own)} forks · {stars} estrelas nos repositórios sem fork.**'
    summary += '\n\nLinguagem principal dos repositórios sem fork: **' + ' · '.join(f'{lang} {n}' for lang, n in langs) + '**.'
    if unknown:
        summary += f' Outros **{unknown}** não têm linguagem principal identificada pelo GitHub.'
    summary += f'\n\n<sub>Dados públicos consultados em {date} (UTC). Cada repositório conta uma vez, pela linguagem principal informada pelo GitHub. Esses números não representam tempo de experiência nem nível de domínio.</sub>'
    readme = ROOT / 'README.md'
    original = readme.read_text(encoding='utf-8')
    updated, count = re.subn(r'<!-- METRICS:START -->.*?<!-- METRICS:END -->',
                            lambda _: '<!-- METRICS:START -->\n' + summary + '\n<!-- METRICS:END -->',
                            original, flags=re.S)
    if count != 1:
        raise ValueError('O README deve conter exatamente um bloco METRICS.')
    rendered = svg(data)
    (ROOT / 'assets').mkdir(exist_ok=True)
    (ROOT / 'assets/github-em-ritmo.svg').write_text(rendered, encoding='utf-8')
    (ROOT / 'assets/dados-publicos.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    readme.write_text(updated, encoding='utf-8')
    print(f'Painel atualizado: {len(repos)} repositórios públicos, {len(own)} sem fork, {len(langs)} linguagens principais.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Gerar sem rede a partir de um snapshot existente.')
    args = parser.parse_args()
    update(json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else collect())
