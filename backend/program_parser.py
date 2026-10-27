"""Extrator determinístico para editais com disciplinas e subitens numerados.

O Gemini continua disponível para documentos não estruturados. Este módulo
nunca resume texto: preserva a redação dos subitens e audita sua cobertura.
"""
import re
import unicodedata

# Cabeçalho de disciplina: 1. LÍNGUA PORTUGUESA (não 1.1 Conteúdo)
SUBJECT = re.compile(r'^\s*(\d{1,2})\.\s+([A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ][^\n]{2,115})\s*$', re.M)
# Subitem com dois ou mais níveis: 1.1, 1.1.1, 4.2.2.3.5
ITEM = re.compile(r'(?<![\w/])(?P<id>\d{1,2}(?:\.\d+){1,8})\.(?=\s|[A-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ])|(?<![\w/])(?P<bare>\d{1,2}(?:\.\d+){1,8})(?=\s)', re.U)
SCOPE = re.compile(r'^\s*(?:CONHECIMENTOS\s+|CONTEÚDO\s+|ANEXO\s+|PERITO\s+CRIMINAL\s*$)', re.I)


def _clean(text):
    return re.sub(r'\s+', ' ', text).strip()


def _fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).casefold()


def _valid_subject(name):
    name = name.strip()
    if not 3 <= len(name) <= 100 or name.endswith(('.', ';', ':')):
        return False
    letters = [c for c in name if c.isalpha()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < .72:
        return False
    if SCOPE.match(name):
        return False
    return True


def parse_numbered_program(pages):
    """Retorna (disciplinas, auditoria). Nunca confunde numeração entre seções.

    Um mesmo identificador pode reaparecer em Conhecimentos Básicos e
    Conhecimentos Específicos: os grupos permanecem separados internamente.
    """
    source = '\n'.join(f'\n[[PAGINA:{page}]]\n{text}' for page, text in pages)
    heads = [m for m in SUBJECT.finditer(source) if _valid_subject(m.group(2))]
    results = []
    uncovered = []
    raw_count = 0
    for i, head in enumerate(heads):
        start = head.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(source)
        body = source[start:end]
        # Os marcadores de página são metadados, não parte do edital.
        body = re.sub(r'\[\[PAGINA:\d+\]\]', lambda m: ' ' * len(m.group()), body)
        # Descarta o início do próximo bloco de conhecimentos, se houver,
        # evitando associar o cabeçalho de seção à última disciplina.
        section = re.search(r'(?m)^\s*CONHECIMENTOS\s+(?:BÁSICOS|GERAIS|ESPECÍFICOS)\b', body)
        if section:
            body = body[:section.start()]
        matches = [m for m in ITEM.finditer(body) if (m.group('id') or m.group('bare')).split('.')[0] == head.group(1)]
        # Só consideramos a seção estruturada quando há itens do seu número.
        if not matches:
            continue
        name = _clean(head.group(2))
        topics = []
        for j, match in enumerate(matches):
            label = match.group('id') or match.group('bare')
            stop = matches[j+1].start() if j+1 < len(matches) else len(body)
            tail = body[match.end():stop]
            # Cabeçalhos de página e número isolado não fazem parte dos tópicos.
            tail = re.sub(r'(?m)^\s*\d{1,3}\s*$', ' ', tail)
            title = _clean(label + ' ' + tail)
            if len(title) < len(label)+3:
                uncovered.append({'disciplina':name,'codigo':label,'motivo':'Item sem descrição legível'})
                continue
            topics.append({'texto':title, 'pagina':_page_for(source, head.end()+match.start()), 'evidencia':title, 'codigo':label, 'origem':'edital_literal'})
            raw_count += 1
        if topics:
            results.append({'nome':name, 'topicos':topics, 'grupo':head.group(1)})
    # Não declara cobertura integral quando o documento não tem estrutura numérica suficiente.
    audit = {'metodo':'numeracao_literal', 'itens_identificados':raw_count + len(uncovered),
             'itens_extraidos':raw_count, 'pendencias':uncovered,
             'disciplinas_identificadas':len(results),
             'confianca_estrutura':'alta' if len(results)>=2 and raw_count>=12 else 'insuficiente'}
    return results, audit


def _page_for(source, position):
    hits = list(re.finditer(r'\[\[PAGINA:(\d+)\]\]', source[:position]))
    return int(hits[-1].group(1)) if hits else None
