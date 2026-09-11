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
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="216" viewBox="0 0 1100 216" role="img" aria-labelledby="title">',
             '<title id="title">GitHub público — André Albson</title>',
             '<style>text{font-family:Arial,Helvetica,sans-serif}</style>',
             '<rect x="1" y="1" width="1098" height="214" rx="18" fill="#101923" stroke="#2a394b"/>',
             text(32, 35, 'GITHUB / REGISTRO PÚBLICO', 12, '#79e6ce', 'letter-spacing="2"')]
    metrics = [(len(repos), 'REPOSITÓRIOS PÚBLICOS'), (len(own), 'SEM FORK'), (len(repos)-len(own), 'FORKS'), (stars, 'ESTRELAS · SEM FORK')]
    for i, (n, label) in enumerate(metrics):
        x = 32 + i*272
        parts += [text(x, 109, n, 46, '#ecf2fa', 'font-weight="700"'), text(x, 138, label, 12, '#a5b4c8', 'letter-spacing="1"')]
        if i:
            parts.append(f'<path d="M{x-22} 64v83" stroke="#2a394b"/>')
    parts += ['<path d="M32 165H1068" stroke="#2a394b"/>',
              text(32, 193, 'Repositórios e estrelas não medem proficiência.', 13, '#a5b4c8'),
              text(1068, 193, f'Consulta: {date} · UTC', 12, '#a5b4c8', 'text-anchor="end"'), '</svg>']
    return '\n'.join(parts) + '\n'


def update(data):
    if data['username'] != USER:
        raise ValueError('Snapshot de outro usuário.')
    repos, own, langs, stars = summarize(data)
    date = datetime.strptime(data['consulted_at'], '%Y-%m-%d').strftime('%d/%m/%Y')
    unknown = len(own) - sum(n for _, n in langs)
    summary = f'**{len(repos)} repositórios públicos · {len(own)} sem fork · {len(repos)-len(own)} forks · {stars} estrelas nos repositórios sem fork.**'
    summary += f'\n\n<sub>Dados públicos consultados em {date} (UTC). Contagens de repositórios e estrelas descrevem a conta, não o nível de domínio de uma tecnologia.</sub>'
    readme = ROOT / 'README.md'
    original = readme.read_text(encoding='utf-8')
    updated, count = re.subn(r'<!-- METRICS:START -->.*?<!-- METRICS:END -->',
                            lambda _: '<!-- METRICS:START -->\n' + summary + '\n<!-- METRICS:END -->',
                            original, flags=re.S)
    if count != 1:
        raise ValueError('O README deve conter exatamente um bloco METRICS.')
    rendered = svg(data)
    (ROOT / 'assets').mkdir(exist_ok=True)
    (ROOT / 'assets/github-publico.svg').write_text(rendered, encoding='utf-8')
    (ROOT / 'assets/dados-publicos.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    readme.write_text(updated, encoding='utf-8')
    print(f'Painel atualizado: {len(repos)} repositórios públicos, {len(own)} sem fork, {len(langs)} linguagens principais.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Gerar sem rede a partir de um snapshot existente.')
    args = parser.parse_args()
    update(json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else collect())
