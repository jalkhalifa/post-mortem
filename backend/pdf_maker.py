"""PDFs gerados por ReportLab: links internos e checkboxes AcroForm."""
from io import BytesIO
from collections import defaultdict
from datetime import date
from pathlib import Path
import os

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

GOLD = HexColor('#CBA453')
BG = HexColor('#0D0D0D')
WHITE = HexColor('#F4F0E7')
MUTED = HexColor('#C9C1B2')
W, H = 595.28, 841.89


def register_fonts():
    """Procura um par regular/negrito de fontes TTF em Windows, Linux e macOS."""
    windir = Path(os.environ.get('WINDIR', r'C:\Windows'))
    candidates = [
        (windir / 'Fonts' / 'arial.ttf', windir / 'Fonts' / 'arialbd.ttf'),
        (windir / 'Fonts' / 'calibri.ttf', windir / 'Fonts' / 'calibrib.ttf'),
        (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
         Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')),
        (Path('/Library/Fonts/Arial.ttf'), Path('/Library/Fonts/Arial Bold.ttf')),
    ]
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont('PM', str(regular)))
            pdfmetrics.registerFont(TTFont('PMBold', str(bold)))
            return
    raise RuntimeError(
        'Nenhuma fonte TTF compatível encontrada. No Windows, verifique '
        'se existem C:\\Windows\\Fonts\\arial.ttf e arialbd.ttf.'
    )


register_fonts()


def page(c, title, subtitle='', page_no=None):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.setFont('PMBold', 13)
    c.drawString(36, H - 40, 'POST MORTEM')
    c.setFont('PM', 8)
    c.drawRightString(W - 36, H - 38, 'DISSECANDO O EDITAL')
    c.setStrokeColor(GOLD)
    c.setLineWidth(.6)
    c.line(36, H - 52, W - 36, H - 52)
    c.setFont('PMBold', 17)
    c.setFillColor(WHITE)
    c.drawString(36, H - 85, str(title)[:55])
    if subtitle:
        c.setFont('PM', 9)
        c.setFillColor(MUTED)
        c.drawString(36, H - 102, str(subtitle)[:90])
    c.setStrokeColor(HexColor('#51422C'))
    c.line(36, 45, W - 36, 45)
    c.setFont('PM', 8)
    c.setFillColor(MUTED)
    c.drawString(36, 30, 'Material de planejamento • POST MORTEM')
    if page_no is not None:
        c.drawRightString(W - 36, 30, str(page_no))


def text_lines(c, text, x, y, maxw=495, size=9, leading=15, color=WHITE, bold=False):
    font = 'PMBold' if bold else 'PM'
    c.setFillColor(color)
    c.setFont(font, size)
    for line in simpleSplit(str(text), font, size, maxw):
        c.drawString(x, y, line)
        y -= leading
    return y


def create_schedule(plan):
    """Capa + instruções + semana por página (com continuação quando necessário) + índice.

    Mantém caixas AcroForm, evita cortes e não comprime textos longos.
    """
    from datetime import timedelta
    b=BytesIO();c=canvas.Canvas(b,pagesize=(W,H),pageCompression=1)
    c.setTitle('POST MORTEM | Planejamento Interativo')
    c.setAuthor('POST MORTEM | Dissecando o edital')
    accent=HexColor('#151A20');border=HexColor('#30333A')
    def bg():
        c.setFillColor(BG);c.rect(0,0,W,H,stroke=0,fill=1)
        c.setFillColor(GOLD);c.rect(0,H-7,W,7,stroke=0,fill=1)
    def footer(number):
        c.setStrokeColor(border);c.line(36,47,W-36,47)
        c.setFont('PMBold',7.4);c.setFillColor(GOLD)
        c.drawString(36,32,'POST MORTEM | DISSECANDO O EDITAL')
        c.setFillColor(MUTED);c.drawRightString(W-36,32,f'{number:02d}')
    def wrap(value,font,size,maxwidth):
        return simpleSplit(str(value),font,size,maxwidth) or ['']
    def draw_lines(lines,x,y,font='PM',size=8,leading=12,color=WHITE):
        c.setFillColor(color);c.setFont(font,size)
        for line in lines:
            c.drawString(x,y,line);y-=leading
        return y
    def safe_lines(value,font,size,width,max_lines=None):
        lines=wrap(value,font,size,width)
        if max_lines is not None and len(lines)>max_lines:
            return lines[:max_lines-1]+[lines[max_lines-1].rstrip()+'…']
        return lines
    def date_br(s):
        d=date.fromisoformat(s);return d.strftime('%d/%m/%Y')
    def header(title,subtitle,number):
        bg();c.setFont('PMBold',9);c.setFillColor(GOLD)
        c.drawString(37,H-40,'CRONOGRAMA DE ESTUDOS')
        c.setFont('PMBold',21);c.setFillColor(WHITE);c.drawString(37,H-75,title)
        c.setFont('PM',9);c.setFillColor(MUTED);c.drawString(37,H-94,subtitle)
        footer(number)
    # Capa: preserva hierarquia e estética do exemplo aprovado.
    bg();c.bookmarkPage('inicio')
    logo=Path(__file__).resolve().parents[1]/'post-mortem'/'assets'/'logo-post-mortem-transparente.png'
    if logo.exists():
        try:c.drawImage(str(logo),W/2-100,H-215,width=200,height=112,preserveAspectRatio=True,anchor='c',mask='auto')
        except Exception:pass
    c.setFillColor(GOLD);c.setFont('PMBold',10);c.drawString(40,H-255,'PLANEJAMENTO INTERATIVO')
    y=H-292
    for title in (plan.get('concurso') or 'CONCURSO', (plan.get('cargo') or 'CARGO') + (' — ' + plan['area'] if plan.get('area') else '')):
        lines=safe_lines(title.upper(),'PMBold',19,W-80,3)
        y=draw_lines(lines,40,y,'PMBold',19,24)-10
    y-=9;y=draw_lines(safe_lines(plan.get('nome','ALUNO').upper(),'PMBold',12,W-80,2),40,y,'PMBold',12,18)-24
    c.setFillColor(accent);c.roundRect(38,y-125,W-76,125,10,stroke=0,fill=1)
    summary=plan['resumo'];_start=date.fromisoformat(plan['inicio']);_end=date.fromisoformat(plan['fim']);week_count=(_end-(_start-timedelta(days=_start.weekday()))).days//7+1
    for j,line in enumerate([f'{week_count} SEMANAS  |  {date_br(plan["inicio"])} — {date_br(plan["fim"])}',
       f'{summary["tarefas_conteudo"]} ATIVIDADES  |  {summary["revisoes"]} REVISÕES',
       f'{summary["simulados"]} SIMULADOS  |  {summary["redacoes"]} REDAÇÕES',
       'PDF · VIDEOAULA · QUESTÕES — CONFORME A DISCIPLINA']):
        draw_lines(safe_lines(line,'PMBold',8,W-115,2),52,y-23-j*26,'PMBold',8,11,GOLD if j==0 else WHITE)
    draw_lines(wrap('Conteúdos informados pelo usuário; confira a cobertura com o edital.', 'PM',8,W-90),40,max(91,y-170),'PM',8,12,MUTED)
    footer(1);c.showPage()
    header('COMO UTILIZAR','Orientações para acompanhar seu planejamento',2)
    y=H-139
    sections=[('MÉTODOS DE ESTUDO','PDF: leitura dos tópicos. VIDEOAULA: aulas conforme quantidade informada. QUESTÕES: resolução e correção. MISTO: combine as atividades de acordo com o método escolhido.'),
       ('BLOCOS DE TEMPO','Cada atividade corresponde a um bloco de 45 minutos. Dias selecionados sem atividades aparecem como tempo livre, sem caixa de seleção.'),
       ('REVISÕES E SIMULADOS','As revisões usam blocos livres. Simulados e redações aparecem nas datas planejadas. Se não houver tempo livre, o sistema sinaliza a limitação.'),
       ('CONTROLE INTERATIVO','Marque as caixas ao concluir cada atividade e salve uma cópia do PDF em um leitor compatível com formulários.'),
       ('EDITAL E COBERTURA','Confira os tópicos com o anexo oficial. O índice final lista os tópicos fornecidos; a IA não garante que o edital inteiro tenha sido extraído.')]
    if plan.get('ciclo_semanal')=='alternado' and plan.get('grupos_ab'):
        sections.append(('SEMANAS A/B','As matérias são agrupadas em semanas A e B alternadas. Para não omitir conteúdos, uma atividade pode aparecer na semana do outro grupo se necessário.'))
    for title,body in sections:
        c.setFillColor(GOLD);c.setFont('PMBold',10);c.drawString(42,y,title);y-=23
        lines=wrap(body,'PM',9,W-88);y=draw_lines(lines,42,y,'PM',9,15,MUTED)-24
    c.showPage()
    # Semanas CIVIS: sempre de segunda a domingo. A primeira/última pode ser parcial.
    weeks=defaultdict(list);start=date.fromisoformat(plan['inicio'])
    first_monday=start-timedelta(days=start.weekday())
    for day in plan['dias']:
        idx=(date.fromisoformat(day['data'])-first_monday).days//7
        weeks[idx].append(day)
    # Uma semana por página quando couber; em semanas densas, continua sem cortar caixas.
    page_num=2;checkbox_counter=0
    daynames=['SEGUNDA','TERÇA','QUARTA','QUINTA','SEXTA','SÁBADO','DOMINGO']
    cycle_ab=plan.get('ciclo_semanal')=='alternado' and bool(plan.get('grupos_ab'))
    for week,days in sorted(weeks.items()):
        entries=[]
        for day in days:
            d=date.fromisoformat(day['data'])
            rows=[]
            for task in day['tarefas']:
                # Separar o titulo da disciplina do conteudo, com altura medida
                # pelo numero real de linhas; nunca cortar nomes ou topicos.
                subject_lines=wrap(f"{task['subject']}  ·  {task['type'].upper()}",'PMBold',7.6,W-126)
                topic_lines=wrap(task['title'],'PM',8.0,W-126)
                row_height=11*len(subject_lines)+12*len(topic_lines)+10
                rows.append((task,(subject_lines,topic_lines),row_height))
            if not rows:
                rows.append((None,['SEM ATIVIDADE PROGRAMADA • tempo disponível para reforço ou descanso'],25))
            # Divide dias excepcionalmente densos em cartões de continuação.
            max_card=H-175
            batch=[];batch_h=34
            for row in rows:
                if batch and batch_h+row[2]>max_card:
                    entries.append((day,d,batch,batch_h))
                    batch=[];batch_h=34
                batch.append(row);batch_h+=row[2]
            if batch:
                entries.append((day,d,batch,batch_h))
        current=[];current_height=0;groups=[]
        for entry in entries:
            if current and current_height+entry[3]+7>H-165:
                groups.append(current);current=[];current_height=0
            current.append(entry);current_height+=entry[3]+7
        if current:groups.append(current)
        for part,group in enumerate(groups,1):
            page_num+=1
            title=f'SEMANA {week+1:02d}' + (f'  |  SEMANA {"A" if week%2==0 else "B"}' if cycle_ab else '')
            suffix=f'  •  PARTE {part}/{len(groups)}' if len(groups)>1 else ''
            # Exibir intervalo da semana civil, limitado pelo início/fim do plano.
            monday=first_monday+timedelta(days=week*7)
            week_begin=max(monday,date.fromisoformat(plan['inicio']))
            week_end=min(monday+timedelta(days=6),date.fromisoformat(plan['fim']))
            date_range=f'{week_begin.strftime("%d/%m/%Y")} A {week_end.strftime("%d/%m/%Y")}{suffix}'
            header(title,date_range,page_num)
            if week==0 and part==1:c.bookmarkPage('semana0')
            y=H-125
            for day,d,rows,height in group:
                top=y;bottom=y-height
                c.setFillColor(accent);c.roundRect(36,bottom,W-72,height,8,stroke=0,fill=1)
                c.setFont('PMBold',9);c.setFillColor(GOLD)
                c.drawString(47,top-17,f'{daynames[d.weekday()]}  •  {d.strftime("%d/%m")}')
                yy=top-35
                for task,lines,row_h in rows:
                    if task is None:
                        draw_lines(lines,49,yy+6,'PM',7.5,12,MUTED)
                    else:
                        checkbox_counter+=1
                        subject_lines,topic_lines=lines
                        # A caixa fica alinhada com o titulo (nao abaixo da linha).
                        # O topico ocupa uma segunda faixa com recuo identico.
                        baseline=yy+5
                        c.acroForm.checkbox(name=f'atividade_{checkbox_counter:05d}',tooltip=(task['subject']+' '+task['title'])[:100],x=49,y=baseline-2,size=10,buttonStyle='check',borderWidth=1,borderColor=GOLD,fillColor=accent,textColor=GOLD,checked=False,forceBorder=True)
                        draw_lines(subject_lines,67,baseline,'PMBold',7.6,11,GOLD)
                        draw_lines(topic_lines,67,baseline-11*len(subject_lines)-2,'PM',8,12,WHITE)
                    yy-=row_h
                y=bottom-7
            c.setFillColor(MUTED);c.setFont('PM',7.4)
            c.drawString(39,58,'Marque cada atividade concluída. Salve o PDF para preservar o progresso.')
            c.showPage()
    # Índice auditável do que foi informado, sem alegar cobertura do edital completo.
    items=list(plan['resumo']['disciplinas'].items());page_num+=1
    header('ÍNDICE DE COBERTURA','Atividades e tópicos fornecidos para cada disciplina',page_num)
    y=H-136
    for name,counts in items:
        lines=wrap(name,'PMBold',9,W-95)
        needed=len(lines)*15+21
        if y-needed<75:
            c.showPage();page_num+=1;header('ÍNDICE DE COBERTURA','Continuação',page_num);y=H-136
        y=draw_lines(lines,42,y,'PMBold',9,15,GOLD)
        ab=f"  |  Grupo {plan['grupos_ab'][name]}" if name in plan.get('grupos_ab',{}) else ''
        detail=f"{counts['topicos']} tópicos informados  ·  {counts['videoaulas']} videoaulas  ·  {counts['tarefas']} atividades{ab}"
        y=draw_lines(wrap(detail,'PM',8,W-95),42,y-1,'PM',8,13,MUTED)-13
    c.save();return b.getvalue()

def create_guide(plan):
    b = BytesIO()
    c = canvas.Canvas(b, pagesize=(W, H), pageCompression=1)
    c.setTitle('POST MORTEM | Guia Rápido de Utilização')
    c.setAuthor('POST MORTEM')
    sections = [
        ('Como usar seu cronograma', [
            '1. Abra o arquivo Cronograma Interativo em um leitor de PDF compatível.',
            '2. Confira concurso, cargo, período e todas as disciplinas.',
            '3. Cada linha representa uma atividade planejada em um bloco de 45 minutos.',
            '4. Marque a caixa de seleção após concluir a atividade.',
            '5. Salve uma cópia preenchida para preservar seu progresso.',
            '6. Caso uma atividade não seja concluída, ajuste manualmente o planejamento.',
        ]),
        ('Métodos de estudo e organização', [
            'PDF: cada tópico informado e aprovado aparece como atividade individual.',
            'Videoaulas: as aulas numeradas seguem a quantidade informada no formulário.',
            'PDF + videoaulas: combina tópicos com as aulas cadastradas.',
            'PDF + questões: inclui um bloco de PDF e outro de questões por tópico.',
            'Revisões semanais, quinzenais ou mensais usam blocos livres.',
            'O sistema não considera conteúdo inexistente no edital como obrigatório.',
        ]),
        ('Limites, conferência e segurança', [
            'A extração de tópicos por IA é uma sugestão que deve ser revisada.',
            'Confira cada tópico com o edital oficial antes de usar o plano.',
            'O sistema não garante aprovação, aprendizado ou cobertura de tópicos omitidos na entrada.',
            'Os horários representam blocos de estudo, não horários fixos do relógio.',
            'Os botões e caixas dependem do aplicativo leitor de PDF.',
            'Não compartilhe seu edital se ele contiver dados pessoais desnecessários.',
        ]),
    ]
    for i, (title, lines) in enumerate(sections, 1):
        page(c, title, 'Guia rápido de utilização | ' + plan['nome'], i)
        y = H - 150
        for line in lines:
            y = text_lines(c, line, 42, y, maxw=500, size=10, leading=19) - 17
        y -= 25
        text_lines(c, 'POST MORTEM | Dissecando o edital',
                   42, y, size=12, bold=True, color=GOLD)
        c.showPage()
    c.save()
    return b.getvalue()
