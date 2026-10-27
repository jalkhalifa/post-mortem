"""Extração auditável do conteúdo programático; não envia edital administrativo inteiro à IA."""
import json
import os
import re
import unicodedata

import pymupdf as fitz
import httpx
from .program_parser import parse_numbered_program


class ExtractionError(ValueError):
    pass


def _fold(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value)) if not unicodedata.combining(c)).casefold()


def _norm(value):
    return re.sub(r'\s+', ' ', str(value)).strip().casefold()


def _subject_key(value):
    """Concilia somente qualificadores genéricos; não mistura Penal e Processo Penal."""
    key = _fold(value)
    key = re.sub(r'[^a-z0-9]+', ' ', key).strip()
    key = re.sub(r'^(?:nocoes de|nocoes sobre|fundamentos de|introducao ao|introducao a)\s+', '', key)
    return re.sub(r'\s+', ' ', key)


def pdf_pages(data):
    if len(data) > 12 * 1024 * 1024:
        raise ExtractionError('O PDF excede 12 MB. Envie o anexo do conteúdo programático em PDF.')
    try:
        doc = fitz.open(stream=data, filetype='pdf')
        if doc.is_encrypted:
            raise ExtractionError('PDF protegido por senha.')
        if doc.page_count > 180:
            raise ExtractionError('PDF com mais de 180 páginas. Envie o anexo do conteúdo programático.')
        # Só recorta a faixa inferior quando identifica um bloco isolado
        # com o número da página. Evita apagar conteúdo legítimo próximo
        # ao rodapé de PDFs que não possuem paginação.
        pages = []
        for i, page in enumerate(doc):
            number = str(i + 1)
            cutoff = page.rect.y1 - min(45, page.rect.height * 0.05)
            footer_is_page_number = any(
                block[1] >= cutoff
                and re.fullmatch(r'(?:\s*' + re.escape(number) + r'\s*){1,3}', block[4] or '')
                for block in page.get_text('blocks')
                if len(block) >= 5 and isinstance(block[4], str)
            )
            if footer_is_page_number:
                body = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, cutoff)
                content = page.get_text('text', sort=True, clip=body)
            else:
                content = page.get_text('text', sort=True)
            pages.append((i + 1, content.strip()))
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError('Não foi possível ler o PDF: ' + str(exc)[:120]) from exc
    if sum(len(t) for _, t in pages) < 250:
        raise ExtractionError('PDF sem texto pesquisável suficiente. Utilize um PDF pesquisável ou cadastre os tópicos manualmente.')
    return pages


# Cabeçalhos comuns em editais, anexos avulsos e materiais verticalizados.
_PROGRAM_TITLE = re.compile(
    r'(?im)^\s*(?:ANEXO\s+(?:[IVX]+|\d+)\s*[-–:.]?\s*)?'
    r'(?:(?:DOS?\s+)?CONTE[ÚU]DOS?\s+PROGRAM[ÁA]TICOS?'
    r'|PROGRAMA\s+DE\s+PROVA|EDITAL\s+VERTICALIZADO|CONTE[ÚU]DOS?\s+VERTICALIZADOS?)\b'
)
_ADMIN = ('inscricoes', 'isencao', 'taxa de inscricao', 'recursos',
          'cronograma de execucao', 'resultado preliminar', 'convocacao',
          'remuneracao', 'vagas', 'requisitos para investidura')
_SUBJECTS = (
    'lingua portuguesa', 'portugues', 'raciocinio logico', 'matematica',
    'informatica', 'direito penal', 'direito processual penal',
    'direito constitucional', 'direito administrativo', 'direitos humanos',
    'legislacao', 'criminalistica', 'medicina legal', 'biologia', 'quimica',
    'fisica', 'contabilidade', 'arquivologia', 'administracao publica',
    'etica', 'geografia', 'historia', 'redacao', 'atualidades', 'estatistica',
    'criminologia', 'conhecimentos especificos', 'conhecimentos gerais',
)

def _program_evidence(text):
    """Sinais estruturais; nunca usa uma simples menção a 'Anexo II'."""
    folded = _fold(text)
    subject_hits = sum(bool(re.search(r'(?m)^\s*(?:[0-9. -]{0,8})?(?:nocoes de\s+)?' + re.escape(x) + r'\b', folded)) for x in _SUBJECTS)
    list_items = len(re.findall(r'(?m)^\s*(?:[0-9]+(?:\.[0-9]+){0,4}[.)]?|[-•☐✓])\s+\S', text))
    tabular = bool(re.search(r'(?i)disciplina\s*[|;\t]\s*(?:conte[úu]do|assunto|t[óo]pico)', text))
    vertical = any(x in folded for x in ('edital verticalizado', 'conteudo verticalizado', 'conteudos verticalizados', 'verticalizacao do edital'))
    admin_hits = sum(x in folded for x in _ADMIN)
    return subject_hits, list_items, tabular, vertical, admin_hits


def select_program_pages(pages):
    """Aceita anexo, edital completo com seção, ou material programático autônomo.

    A heurística só escolhe páginas; a IA continua obrigada a devolver evidência
    literal para cada tópico. Não usa conteúdo administrativo como programa.
    """
    if not pages:
        raise ExtractionError('PDF sem páginas de texto.')
    candidates = []
    for idx, (_, txt) in enumerate(pages):
        for match in _PROGRAM_TITLE.finditer(txt):
            tail = txt[match.end():]
            # O título pode estar sozinho no final da página: aceita se a
            # próxima página tem características programáticas.
            next_text = pages[idx + 1][1] if idx + 1 < len(pages) else ''
            hits, items, tabular, vertical, _ = _program_evidence(tail + '\n' + next_text[:2500])
            if hits >= 1 or items >= 3 or tabular or vertical:
                candidates.append((idx, match.start()))
                break
    if candidates:
        start_idx, offset = candidates[0]
        selected = []
        for idx in range(start_idx, len(pages)):
            page_no, text = pages[idx]
            if idx == start_idx:
                text = text[offset:]
            if idx > start_idx and re.search(r'(?im)^\s*ANEXO\s+(?:II|III|IV|V|VI|VII|2|3|4|5)\b', text):
                break
            if text.strip():
                selected.append((page_no, text))
            if len(selected) > 45:
                raise ExtractionError('O conteúdo programático ultrapassa 45 páginas. Envie apenas o anexo ou o edital verticalizado.')
        return selected

    # Sem título canônico: arquivo verticalizado ou anexo independente.
    joined = '\n'.join(t for _, t in pages)
    hits, items, tabular, vertical, admin_hits = _program_evidence(joined[:40000])
    is_standalone = (vertical or tabular or (hits >= 2 and items >= 3) or
                     (hits >= 3 and len(pages) <= 12))
    # Materiais curtos de disciplina única: cabeçalho de disciplina + itens.
    if not is_standalone and len(pages) <= 8 and hits >= 1 and items >= 5 and admin_hits == 0:
        is_standalone = True
    if not is_standalone or (admin_hits >= 3 and not (vertical or tabular)):
        raise ExtractionError(
            'Não foi possível identificar conteúdo programático com segurança. '
            'Envie o anexo, um edital verticalizado pesquisável ou o PDF de tópicos. '
            'Se o documento tiver uma estrutura diferente, envie-o para ajustarmos o reconhecimento.'
        )
    if len(pages) > 45:
        raise ExtractionError('Documento programático com mais de 45 páginas. Separe por anexos ou disciplinas.')
    return [(page, text) for page, text in pages if text.strip()]

def _chunks(pages, limit=4800):
    """Divide por linhas, com sobreposição: não parte tópicos no meio sem contexto.

    Para linhas isoladas maiores que o limite, usa janela com sobreposição;
    os itens repetidos são deduplicados depois por disciplina.
    """
    if limit < 600:
        raise ValueError('Limite de trecho insuficiente.')
    chunks = []
    for page, text in pages:
        prefix = f'[PÁGINA {page}]\n'
        budget = limit - len(prefix)
        lines = text.splitlines(keepends=True)
        current = ''
        for line in lines:
            if len(line) > budget:
                if current.strip():
                    chunks.append(prefix + current)
                    current = ''
                step = budget - 350
                for offset in range(0, len(line), step):
                    chunks.append(prefix + line[offset:offset + budget])
                continue
            if len(current) + len(line) > budget:
                if current.strip():
                    chunks.append(prefix + current)
                # Retém cabeçalho/contexto da linha anterior sem perder caracteres.
                prev_lines = current.splitlines(keepends=True)
                context = prev_lines[-1] if prev_lines else ''
                current = context[-min(len(context), 250):] if len(context) < budget - len(line) else ''
            current += line
        if current.strip():
            chunks.append(prefix + current)
    if len(chunks) > 60:
        raise ExtractionError(f'O conteúdo programático exige {len(chunks)} partes; limite seguro desta versão: 60. Envie o anexo separado.')
    return chunks


# Recorte determinístico anterior ao Gemini: nunca confiar apenas no prompt
# para separar áreas com o mesmo cargo.
_AREA_LABEL = re.compile(r'(?i)\b(?:[áa]rea|especialidade|habilita[cç][ãa]o)\s*(?:n[ºo.]?\s*)?([IVXLC]+|\d{1,2})(?=\b|\s*[-–—:])')
_AREA_HEADING = re.compile(r'(?i)^\s*(?:(?:CONHECIMENTOS\s+(?:ESPEC[ÍI]FICOS|GERAIS)\s*[-–—:]?\s*)|(?:CARGO\s*[:–-]\s*))?(?:PERITO\s+(?:CRIMINAL|OFICIAL)[^:]{0,75}?)?\b(?:[ÁA]REA|ESPECIALIDADE|HABILITA[ÇC][ÃA]O)\s*(?:N[ºO.]?\s*)?(?:[IVXLC]+|\d{1,2})\b(?:\s*[-–—:][^\n]{0,90})?\s*$')
_COMMON_HEADING = re.compile(r'(?i)^\s*(?:(?:CONTE[ÚU]DO|CONHECIMENTOS)\s+)?(?:COMUM(?:S| A TODOS OS CARGOS)?|GERAIS(?:\s+A TODOS OS CARGOS)?|B[ÁA]SICOS(?:\s+A TODOS OS CARGOS)?)\s*[:–-]?\s*$')
_ROLE_HEADING = re.compile(r'(?i)^\s*(?:CARGO\s*[:–-]\s*|CONHECIMENTOS\s+ESPEC[ÍI]FICOS\s*[-–—:]\s*)([^\n]{3,100})$')
_ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10,'XI':11,'XII':12,'XIII':13,'XIV':14,'XV':15}

def _area_number(value):
    match=_AREA_LABEL.search(str(value))
    if not match: return None
    token=match.group(1).upper()
    return int(token) if token.isdigit() else _ROMAN.get(token)

def _area_label(value):
    return _fold(str(value)).strip()

# Títulos compostos como "CONHECIMENTOS ESPECÍFICOS AVANÇADOS (ÁREA I)"
# e "CONHECIMENTOS BÁSICOS (ÁREA I e ÁREA II)" são frequentes em editais.
_KNOWLEDGE_SCOPE = re.compile(
    r'(?i)^\s*CONHECIMENTOS\s+(?:B[ÁA]SICOS|GERAIS|ESPEC[ÍI]FICOS(?:\s+B[ÁA]SICOS|\s+AVAN[ÇC]ADOS)?)'
    r'\s*\(\s*((?:[ÁA]REA\s+(?:[IVXLC]+|\d{1,2})\s*(?:e|,|/|ou|\+)\s*)*'
    r'[ÁA]REA\s+(?:[IVXLC]+|\d{1,2}))\s*\)\s*$'
)

def _knowledge_areas(line):
    match = _KNOWLEDGE_SCOPE.match(line.strip())
    if not match:
        return None
    numbers = {_area_number(m.group()) for m in _AREA_LABEL.finditer(match.group(1))}
    return {n for n in numbers if n is not None}


def scope_program_pages(pages, cargo='', area=''):
    """Seleciona conteúdos comuns e específicos de uma área por cabeçalhos.

    Evita interpretar menções administrativas ou itens de matérias como troca de área.
    """
    area = str(area or '').strip()
    cargo = str(cargo or '').strip()
    wanted = _area_number(area) if area else None
    if area and wanted is None and len(_area_label(area)) < 3:
        raise ExtractionError('Informe a área como “Área 1”, “Área II” ou a especialidade completa.')

    seen = set()
    for _, text in pages:
        for line in text.splitlines():
            scoped = _knowledge_areas(line)
            if scoped is not None:
                seen.update(scoped)
            elif _AREA_HEADING.match(line.strip()):
                n = _area_number(line)
                if n is not None:
                    seen.add(n)

    if not area:
        if len(seen) > 1:
            raise ExtractionError('O documento contém várias áreas/especialidades. Informe a área pretendida antes de detectar os tópicos.')
        return pages, {'cargo': cargo, 'area': None, 'areas_encontradas': sorted(seen), 'modo': 'sem_area'}

    if seen and wanted not in seen:
        raise ExtractionError('Área selecionada não encontrada no conteúdo programático. Áreas identificadas: ' + ', '.join('Área ' + str(n) for n in sorted(seen)) + '.')

    output = []
    mode = 'common'
    selected_specific = False
    cargo_key = _subject_key(cargo) if cargo else ''
    role_mode = None
    for page_no, text in pages:
        kept = []
        for line in text.splitlines():
            stripped = line.strip()
            scoped = _knowledge_areas(stripped)
            if scoped is not None:
                # Cabeçalhos que abrangem ambas as áreas são comuns, não exclusivos.
                if wanted in scoped:
                    mode = 'specific' if len(scoped) == 1 else 'common'
                    if len(scoped) == 1:
                        selected_specific = True
                    kept.append(line)
                else:
                    mode = 'other'
                role_mode = None
                continue
            if _COMMON_HEADING.match(stripped):
                mode = 'common'
                role_mode = None
                kept.append(line)
                continue
            if _AREA_HEADING.match(stripped):
                number = _area_number(stripped)
                if number is not None:
                    mode = 'specific' if number == wanted else 'other'
                    if mode == 'specific':
                        selected_specific = True
                else:
                    label = _area_label(stripped)
                    mode = 'specific' if _area_label(area) in label else 'other'
                    if mode == 'specific':
                        selected_specific = True
                if mode == 'specific':
                    kept.append(line)
                role_mode = None
                continue
            role = _ROLE_HEADING.match(stripped)
            if role and not _AREA_LABEL.search(stripped):
                candidate = _subject_key(role.group(1))
                role_mode = 'own' if (cargo_key and (cargo_key in candidate or candidate in cargo_key)) else 'other'
                mode = 'common' if role_mode == 'own' else 'other'
            if mode != 'other' and role_mode != 'other':
                kept.append(line)
        if any(line.strip() for line in kept):
            output.append((page_no, '\n'.join(kept)))

    if not selected_specific:
        raise ExtractionError('Não foi possível identificar com segurança o bloco específico de ' + area + '. Confira o edital ou preencha os tópicos manualmente.')
    if not output:
        raise ExtractionError('Nenhum conteúdo aplicável ao cargo/área selecionado foi encontrado.')
    return output, {'cargo': cargo, 'area': area, 'areas_encontradas': sorted(seen), 'modo': 'comum_e_especifico'}


async def extract_topics(data, names, cargo="", area=""):
    autodetect = names is None
    if not autodetect and (not isinstance(names, list) or not names or len(names) > 65):
        raise ExtractionError('Selecione entre 1 e 65 disciplinas.')
    if autodetect: names = []
    all_pages = pdf_pages(data)
    pages = select_program_pages(all_pages)
    pages, escopo = scope_program_pages(pages, cargo=cargo, area=area)
    # Primeiro, extrai TODOS os itens numerados literalmente, sem IA, sem
    # divisão em blocos e sem limite de tokens. Isso evita truncamentos e
    # omissões em editais como o da PCMG, com 300+ subitens na mesma seção.
    structured, audit = parse_numbered_program(pages)
    if audit['confianca_estrutura'] == 'alta' and not audit['pendencias']:
        # Mantém a redação literal e a ordem. Não divide disciplinas combinadas
        # arbitrariamente: os nomes são os cabeçalhos reais do edital.
        if not autodetect:
            chosen = {_subject_key(x):x for x in names}
            structured = [dict(d, nome=chosen[_subject_key(d['nome'])])
                          for d in structured if _subject_key(d['nome']) in chosen]
            present = {_subject_key(d['nome']) for d in structured}
            structured.extend({'nome':name,'topicos':[]} for name in names
                              if _subject_key(name) not in present)
        audit['itens_retornados'] = sum(len(d['topicos']) for d in structured)
        audit['status'] = 'itens_numerados_conferidos'
        return {'disciplinas':structured,
                'avisos':['Extração literal por numeração: os subitens identificados foram copiados do PDF, sem resumir pelo Gemini.',
                          'Confira também títulos sem numeração, eventuais tabelas e a divisão das disciplinas antes de confirmar.'],
                'paginas_texto':len(pages),'escopo':escopo,'auditoria':audit}
    if not os.getenv('GEMINI_API_KEY', '').strip():
        raise ExtractionError('GEMINI_API_KEY não configurada. Salve sua chave no arquivo .env do projeto e reinicie o servidor.')
    chunks = _chunks(pages)
    instructions = (
        'Você extrai tópicos de concursos públicos sem inventar. Use APENAS conteúdo programático explícito. '
        'Identifique disciplinas pelos cabeçalhos explícitos do conteúdo programático. '        'Reconheça nomes equivalentes com qualificadores como Noções de, Fundamentos de, Introdução a; '        'por exemplo Noções de Direito Penal corresponde a Direito Penal, mas Direito Processual Penal é diferente de Direito Penal. '
        'Não atribua a uma disciplina o conteúdo de outra; não infira itens faltantes. '
        'Se a disciplina não estiver presente neste trecho, devolva lista vazia. '
        'Retorne SOMENTE JSON: {"disciplinas":[{"nome":"nome da disciplina conforme o edital",'
        '"topicos":[{"texto":"assunto do edital","pagina":1,"evidencia":"trecho literal do texto"}]}]}. '
        'A evidência deve ser uma sequência literal contígua presente no trecho; não parafraseie a evidência. '
        'Copie o texto INTEGRAL de cada tópico, sem resumir, sem cortar o final e sem limite artificial de palavras. Não una tópicos distintos e não transforme subtópicos em uma frase genérica. O campo texto deve conter a redação literal do tópico; evidencia deve conter o mesmo texto literal quando possível. Se um item começar neste trecho e terminar no próximo, só extraia a parte completa no trecho que a contiver.'
    )
    if not autodetect:
        instructions += ' MODO SELEÇÃO: retorne somente nomes solicitados, exatamente como enviados. '
    else:
        instructions += (' MODO DESCOBERTA: identifique todas as disciplinas explicitamente nomeadas no trecho, '
                         'sem depender de uma lista prévia. Não crie disciplinas a partir de assuntos soltos. '
                         'Para cada disciplina inclua topicos com evidência literal. ')
    instructions += (' CARGO ALVO: '+str(cargo)[:120]+'. ÁREA/ESPECIALIDADE ALVO: '+str(area or 'não informada')[:120]+'. '
                     'Extraia apenas conteúdos comuns aplicáveis ao cargo e os específicos da área selecionada; não misture outras áreas. ')
    mapping = {_norm(x): x for x in names}
    canonical = {}
    for x in names:
        canonical.setdefault(_subject_key(x), []).append(x)
    out = {name: [] for name in names}
    seen = {name: set() for name in names}
    rejected = 0
    async with httpx.AsyncClient(timeout=120) as client:
        model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip()
        if not re.fullmatch(r'[A-Za-z0-9._-]+', model):
            raise ExtractionError('GEMINI_MODEL inválido no arquivo .env.')

        async def request_json(chunk, label):
            """Uma solicitação; informa a causa sem revelar chave nem conteúdo enviado."""
            body = {
                'systemInstruction': {'parts': [{'text': instructions}]},
                'contents': [{'role': 'user', 'parts': [{'text': ('Identifique todas as disciplinas sem seleção prévia.' if autodetect else 'Disciplinas solicitadas: ' + json.dumps(names, ensure_ascii=False)) + '\n\nCONTEÚDO PROGRAMÁTICO (PARTE ' + label + '):\n' + chunk}]}],
                'generationConfig': {'temperature': 0, 'responseMimeType': 'application/json', 'maxOutputTokens': 8192},
            }
            url = 'https://generativelanguage.googleapis.com/v1beta/models/' + model + ':generateContent'
            try:
                response = await client.post(url, headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'].strip()}, json=body)
            except httpx.HTTPError as exc:
                raise ExtractionError('Falha de conexão com o Google Gemini. Verifique a internet e tente novamente.') from exc
            if response.status_code >= 400:
                status = response.status_code
                if status in (400, 401, 403):
                    hint = 'Chave Gemini inválida, API indisponível para este projeto ou restrição de acesso. Confira a chave no Google AI Studio.'
                elif status == 404:
                    hint = 'Modelo Gemini não encontrado. Confira GEMINI_MODEL e os modelos disponíveis no Google AI Studio.'
                elif status == 429:
                    hint = 'Limite da cota gratuita do Gemini atingido. Aguarde a renovação da cota ou reduza a frequência de extrações.'
                elif status >= 500:
                    hint = 'Serviço do Gemini temporariamente indisponível. Tente novamente mais tarde.'
                else:
                    hint = 'Verifique a configuração da API Gemini.'
                raise ExtractionError(f'Erro da API Gemini (HTTP {status}). {hint} Nenhuma extração parcial foi aprovada.')
            try:
                payload = response.json()
                candidate = payload['candidates'][0]
                reason = candidate.get('finishReason')
                if reason not in (None, 'STOP'):
                    raise ValueError('finishReason=' + str(reason))
                raw = ''.join(part.get('text', '') for part in candidate['content']['parts'])
                result = json.loads(raw)
                entries = result['disciplinas']
                if not isinstance(entries, list):
                    raise ValueError('disciplinas não é lista')
                return entries
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ValueError(str(exc)[:120]) from exc

        async def robust_json(chunk, label, depth=0):
            try:
                return await request_json(chunk, label)
            except ValueError as exc:
                # Resposta truncada (MAX_TOKENS) ou JSON inválido: reduz o trecho
                # e refaz as solicitações. Não aceita JSON parcial ou reparos adivinhados.
                if depth >= 3 or len(chunk) < 450:
                    raise ExtractionError(
                        f'O Gemini retornou JSON inválido ou incompleto na parte {label} '
                        f'({str(exc)[:90]}). Mesmo após dividir o trecho, a extração falhou. '
                        'Nenhum resultado parcial foi aprovado.'
                    ) from exc
                # Corte preferencial por quebra de linha, preservando todo o texto.
                mid = len(chunk) // 2
                left = chunk.rfind('\n', max(0, mid - 400), mid + 400)
                if left < 400 or left > len(chunk) - 400:
                    left = mid
                a = await robust_json(chunk[:left], label + 'a', depth + 1)
                b = await robust_json(chunk[left:], label + 'b', depth + 1)
                return a + b

        for i, chunk in enumerate(chunks, 1):
            entries = await robust_json(chunk, str(i))
            normalized_chunk = _norm(chunk)
            for entry in entries:
                if not isinstance(entry, dict):
                    rejected += 1
                    continue
                name = mapping.get(_norm(entry.get('nome', '')))
                if not name:
                    equivalents = canonical.get(_subject_key(entry.get('nome', '')), [])
                    if len(equivalents) == 1: name = equivalents[0]
                if not name and autodetect:
                    proposed = str(entry.get('nome','')).strip()[:100]
                    if proposed and len(proposed)>=3 and len(out)<65:
                        key = _subject_key(proposed)
                        existing = next((n for n in out if _subject_key(n)==key),None)
                        name = existing or proposed
                        if name not in out:
                            out[name]=[];seen[name]=set()
                if not name:
                    rejected += 1
                    continue
                for topic in entry.get('topicos', [])[:700]:
                    if not isinstance(topic, dict):
                        rejected += 1
                        continue
                    title = str(topic.get('texto', '')).strip()
                    evidence = str(topic.get('evidencia', '')).strip()
                    if not title or not evidence or len(title) > 12000 or len(evidence) > 12000 or _norm(evidence) not in normalized_chunk:
                        rejected += 1
                        continue
                    key = _norm(title)
                    if key not in seen[name]:
                        seen[name].add(key)
                        out[name].append({'texto': title, 'pagina': topic.get('pagina'), 'evidencia': evidence})
    warnings = ['Formato do documento identificado por título ou estrutura; confira todas as disciplinas e tópicos.', 'Disciplinas detectadas automaticamente: confira nomes e tópicos com o edital.' if autodetect else 'Extração com disciplinas selecionadas: confira nomes e tópicos.', 'Extração automática de ' + str(len(chunks)) + ' parte(s): confira cada tópico e o cargo no edital antes de gerar o PDF.']
    if rejected:
        warnings.append(str(rejected) + ' sugestões descartadas por falta de evidência ou disciplina incompatível. Compare especialmente as matérias com poucos tópicos com o documento original.')
    if not any(out.values()):
        warnings.append('Nenhum tópico compatível com as disciplinas selecionadas foi identificado. Confira o anexo e a seleção.')
    return {'disciplinas': [{'nome': name, 'topicos': topics} for name,topics in out.items() if topics or not autodetect], 'avisos': warnings, 'paginas_texto': len(pages), 'escopo': escopo, 'auditoria': {'metodo':'gemini','status':'revisao_manual_obrigatoria','itens_retornados':sum(len(t) for t in out.values()),'pendencias':[]}}
