"""Motor determinístico: nunca inventa tópicos do edital nem excede minutos diários."""
from datetime import date, timedelta
from collections import defaultdict, deque
from dateutil.relativedelta import relativedelta
import math

WEEKDAYS = {'segunda':0,'terca':1,'quarta':2,'quinta':3,'sexta':4,'sabado':5,'domingo':6}

class PlanError(ValueError): pass

def clean_topics(value):
    if not isinstance(value, list): return []
    return list(dict.fromkeys(x.strip() for x in value if isinstance(x,str) and x.strip()))[:700]

def build_plan(profile):
    obj=profile.get('objetivo') or {}; disp=profile.get('disponibilidade') or {}; prefs=profile.get('preferencias') or {}
    try:
        start=date.fromisoformat(obj['inicio']); months=int(obj['meses']); assert 1<=months<=24
        end=start+relativedelta(months=months)-timedelta(days=1)
    except (KeyError,ValueError,TypeError,AssertionError): raise PlanError('Informe data inicial válida e duração de 1 a 24 meses.')
    days=set(disp.get('dias') or [])
    if not days or not days.issubset(WEEKDAYS): raise PlanError('Selecione dias válidos de estudo.')
    try:
        hours=[float(disp.get(k,0)) for k in ['horasDiasUteis','horasSabado','horasDomingo']]
    except (TypeError,ValueError): raise PlanError('Confira as horas disponíveis.')
    if any(not math.isfinite(v) or v<0 or v>12 for v in hours): raise PlanError('Horas devem estar entre 0 e 12.')
    slots=[]; d=start
    while d<=end:
        if d.weekday() in [WEEKDAYS[x] for x in days]:
            h=hours[0] if d.weekday()<5 else hours[1] if d.weekday()==5 else hours[2]
            # Blocos de 45 min. Sobras menores que 45 min ficam livres, nunca ultrapassamos o tempo disponível.
            for i in range(int(h*60)//45): slots.append({'date':d.isoformat(),'slot':i,'task':None})
        d+=timedelta(days=1)
    if not slots: raise PlanError('Não há blocos de 45 minutos nos dias selecionados.')
    subjects=profile.get('disciplinas') or []
    if not isinstance(subjects,list) or not subjects or len(subjects)>65: raise PlanError('Selecione entre 1 e 65 disciplinas.')
    buckets=[]; missing=[]; missing_videos=[]; coverage={}; seen_names=set(); warnings=[]
    for s in subjects:
        name=str(s.get('nome','')).strip()[:100]; method=s.get('metodo','pdf')
        if not name or name.casefold() in seen_names: raise PlanError('Confira os nomes e duplicações das disciplinas.')
        seen_names.add(name.casefold())
        if method not in ('pdf','video','misto','pdf_questoes','questoes'): raise PlanError('Método inválido em '+name)
        topics=clean_topics(s.get('topicos'))
        if method in ('pdf','misto','pdf_questoes') and not topics: missing.append(name)
        if method=='questoes' and not topics: missing.append(name)
        tasks=[]
        if method in ('pdf','misto','pdf_questoes','questoes'):
            for i,t in enumerate(topics): tasks.append({'type':'questoes' if method=='questoes' else 'conteudo','subject':name,'title':t,'topic_id':f'{name}:{i+1}'})
        if method=='pdf_questoes':
            paired=[]
            for i,t in enumerate(topics):
                paired.extend([tasks[i],{'type':'questoes','subject':name,'title':'Resolver questões — '+t,'topic_id':f'{name}:questoes:{i+1}'}])
            tasks=paired
        n=s.get('quantidadeVideoaulas')
        if method in ('video','misto'):
            if n in ('',None):
                missing_videos.append(name)
            else:
                try: n=int(n); assert 1<=n<=1500
                except (ValueError,TypeError,AssertionError): raise PlanError('Quantidade de videoaulas inválida em '+name)
                for i in range(n): tasks.append({'type':'video','subject':name,'title':f'Videoaula {i+1} de {n}','topic_id':f'{name}:video:{i+1}'})
        coverage[name]={'topicos':len(clean_topics(s.get('topicos'))),'videoaulas':n if isinstance(n,int) else 0,'tarefas':len(tasks)}
        buckets.append(deque(tasks))
    if missing or missing_videos:
        errors=[]
        if missing: errors.append('Inclua os tópicos de PDF/Misto/Questões: '+', '.join(missing)+'.')
        if missing_videos: errors.append('Informe a quantidade de videoaulas: '+', '.join(missing_videos)+'.')
        raise PlanError(' '.join(errors)+' Não geramos tópicos nem quantidades fictícias.')
    # Semana A/B é uma preferência opcional: alterna as matérias, sem suprimir
    # tópicos ou limitar rigidamente a capacidade das semanas.
    cycle=prefs.get('cicloSemanal','tradicional')
    if cycle not in ('tradicional','alternado'):
        raise PlanError('Organização semanal inválida.')
    alternating=(cycle=='alternado' and len(subjects)>1)
    subject_groups={}
    if alternating:
        # Particiona disciplinas equilibrando a quantidade real de tarefas,
        # e não apenas o número de matérias.
        loads=[0,0]
        for name,weight in sorted(((s['nome'].strip(),len(q)) for s,q in zip(subjects,buckets)),
                                  key=lambda item:(-item[1],item[0].casefold())):
            side=0 if loads[0]<=loads[1] else 1
            subject_groups[name]='A' if side==0 else 'B'
            loads[side]+=weight
    # Mantém a ordem de cada disciplina e agrupa tarefas em sessões pedagógicas.
    # Videoaulas: 2–3 por sessão quando houver blocos suficientes no dia.
    mandatory=[]; sessions=[]
    max_day_slots=max((sum(1 for sl in slots if sl['date']==day) for day in {sl['date'] for sl in slots}),default=1)
    for queue in buckets:
        tasks=list(queue)
        mandatory.extend(tasks)
        k=0; group=[]
        while k<len(tasks):
            item=tasks[k]
            if item['type']=='video': size=min(3,max_day_slots)
            elif item['type']=='questoes': size=min(2,max_day_slots)
            elif item['type']=='conteudo' and k+1<len(tasks) and tasks[k+1]['type']=='questoes': size=min(2,max_day_slots)
            else: size=1
            group.append(tasks[k:k+size]);k+=size
        sessions.append(group)
    if len(mandatory)>5000: raise PlanError('Mais de 5.000 atividades. Divida o edital em um planejamento menor.')
    # Simulados/redações: reservar a quantidade solicitada, com distribuição uniforme no período.
    special=[]; sims=prefs.get('simulados') or {}; writing=prefs.get('redacao') or {}
    total_days=(end-start).days+1
    def count_events(config, freq_key, active):
        if not active: return 0
        n=config.get('quantidade')
        if n not in ('',None):
            try: n=int(n); assert 1<=n<=100
            except (ValueError,TypeError,AssertionError): raise PlanError('Quantidade de simulados/redações inválida.')
            return n
        freq=config.get(freq_key,'')
        period={'semanal':7,'quinzenal':14,'mensal':30}.get(freq,30)
        return max(1,math.ceil(total_days/period))
    sim_n=count_events(sims,'frequencia',sims.get('opcao')=='sim')
    write_n=count_events(writing,'frequencia',bool(writing.get('produzir')))
    for i in range(sim_n): special.append({'type':'simulado','subject':'Simulado','title':f'Simulado {i+1}/{sim_n}','slots':2,'progress':(i+.5)/sim_n})
    for i in range(write_n):
        special.append({'type':'redacao','subject':'Redação','title':f'Produção de redação {i+1}/{write_n}','slots':2,'progress':(i+.5)/write_n})
        if writing.get('reservarRevisao'): special.append({'type':'correcao','subject':'Redação','title':f'Revisar redação {i+1}/{write_n}','slots':1,'progress':min(.99,(i+.7)/write_n)})
    special.sort(key=lambda x:x['progress'])
    required=len(mandatory)+sum(t['slots'] for t in special)
    if required>len(slots):
        raise PlanError(f'Planejamento inviável: {required} blocos de 45 min necessários para conteúdos, simulados e redações; apenas {len(slots)} disponíveis. Aumente o prazo/horas ou reduza atividades opcionais.')
    # Reservar atividades especiais em dias próximos das datas distribuídas, sem sobreposição.
    bydate=defaultdict(list)
    for idx,slot in enumerate(slots): bydate[slot['date']].append(idx)
    for task in special:
        target=start+timedelta(days=int(task['progress']*max(0,total_days-1)))
        options=sorted(bydate, key=lambda day:(abs((date.fromisoformat(day)-target).days),day))
        found=False
        for day in options:
            free=[i for i in bydate[day] if slots[i]['task'] is None]
            if len(free)>=task['slots']:
                for part,j in enumerate(free[:task['slots']],1):
                    item={k:v for k,v in task.items() if k not in ('slots','progress')}
                    if task['slots']>1:item['title']+=f' — bloco {part}/{task["slots"]}'
                    slots[j]['task']=item
                found=True; break
        if not found: raise PlanError('Não foi possível reservar um dia para um simulado ou redação; ajuste a disponibilidade.')
    # Distribuição por SEMANAS DE CALENDÁRIO, concentrando blocos da mesma
    # disciplina no mesmo dia e evitando muitas matérias por dia quando possível.
    weeks=sorted({(date.fromisoformat(s['date'])-timedelta(days=date.fromisoformat(s['date']).weekday())).isoformat() for s in slots})
    week_number={w:i for i,w in enumerate(weeks)}
    def week_for(day):
        d=date.fromisoformat(day)
        return week_number[(d-timedelta(days=d.weekday())).isoformat()]
    scheduled=[]
    for groups in sessions:
        for i,group in enumerate(groups):
            scheduled.append((int((i+.5)*len(weeks)/len(groups)),group))
    scheduled.sort(key=lambda x:x[0])
    for target,group in scheduled:
        subject=group[0]['subject']
        byday=defaultdict(list)
        for j,s in enumerate(slots):byday[s['date']].append(j)
        candidates=[]
        for day,indices in byday.items():
            free=[j for j in indices if slots[j]['task'] is None]
            if len(free)<len(group):continue
            existing=[slots[j]['task']['subject'] for j in indices if slots[j]['task']]
            week=week_for(day)
            same_week=any(s['task'] and s['task']['subject']==subject and week_for(s['date'])==week for s in slots)
            # Priorizar proximidade da semana-alvo e apenas uma sessão/semana.
            parity_penalty=(28 if alternating and (week%2)!=(0 if subject_groups.get(subject)=='A' else 1) else 0)
            score=(abs(week-target)*12+parity_penalty+(9 if same_week else 0)
                   +len(set(existing)-{subject})*5+len(existing)/max(1,len(indices)))
            candidates.append((score,day,free))
        if candidates:
            _,day,free=min(candidates,key=lambda x:(x[0],x[1]))
            for task,j in zip(group,free):slots[j]['task']=task
        else:
            # Capacidade total suficiente, mas não existe um único dia com
            # blocos consecutivos: repartir, sem eliminar nenhuma atividade.
            remaining=[j for j,s in enumerate(slots) if s['task'] is None]
            remaining.sort(key=lambda j:(abs(week_for(slots[j]['date'])-target),slots[j]['date'],j))
            for task,j in zip(group,remaining):slots[j]['task']=task
            warnings.append(f'{subject}: uma sessão precisou ser dividida entre dias por falta de blocos livres no mesmo dia.')
    # Revisões ocupam apenas blocos livres, sem apagar conteúdos obrigatórios.
    review_mode=prefs.get('revisoes','semanal')
    review_count=0
    if review_mode in ('semanal','quinzenal','mensal'):
        period={'semanal':7,'quinzenal':14,'mensal':30}[review_mode]
        byweek=defaultdict(list)
        for i,s in enumerate(slots): byweek[(date.fromisoformat(s['date'])-start).days//period].append(i)
        for week,indices in byweek.items():
            used=[slots[i]['task'] for i in indices if slots[i]['task'] and slots[i]['task']['type'] in ('conteudo','video','questoes')]
            empty=[i for i in indices if slots[i]['task'] is None]
            if used and empty:
                subjects_week=', '.join(dict.fromkeys(t['subject'] for t in used))
                slots[empty[-1]]['task']={'type':'revisao','subject':'Revisão','title':'Revisar: '+subjects_week,'topic_id':None}
                review_count+=1
        if review_count == 0: warnings.append('Não houve blocos livres para as revisões selecionadas. Aumente as horas ou o prazo para incluir revisões.')
    # Preserve TODOS os dias de estudo com capacidade, mesmo sem atividade.
    # A ausência de tarefas não pode fazer dias desaparecerem do cronograma.
    result=defaultdict(list)
    capacities=defaultdict(int)
    for s in slots:
        capacities[s['date']]+=45
        if s['task']: result[s['date']].append(s['task'])
    assert len([s for s in slots if s['task'] and s['task'].get('topic_id')])==len([t for t in mandatory if t.get('topic_id')])
    if alternating:
        warnings.append('Semana A/B: a alternância é preferencial. Se necessário, atividades podem aparecer na outra semana para preservar todos os tópicos.')
    return {'ciclo_semanal':cycle,'grupos_ab':subject_groups,'inicio':start.isoformat(),'fim':end.isoformat(),'nome':str((profile.get('aluno') or {}).get('nome','Aluno'))[:120], 'concurso':str(obj.get('concurso',''))[:120], 'cargo':str(obj.get('cargo',''))[:120], 'area':str(obj.get('area',''))[:120], 'dias':[{'data':day,'tarefas':result[day],'minutos':45*len(result[day]),'minutos_disponiveis':capacities[day]} for day in sorted(capacities)], 'resumo':{'blocos_disponiveis':len(slots),'blocos_obrigatorios':required,'tarefas_conteudo':len(mandatory),'revisoes':review_count,'simulados':sim_n,'redacoes':write_n,'disciplinas':coverage},'avisos':warnings,'edital_revisado':True}
