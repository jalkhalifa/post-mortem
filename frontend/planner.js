// Gerador local: solicita PDFs e extração ao backend FastAPI.
'use strict';
const form = document.getElementById('formulario');
const list = document.getElementById('disciplinas');
const result = document.getElementById('resultado');
const optionsBox = document.getElementById('materias-opcoes');
const catalog = ["Administração Financeira e Orçamentária", "Administração Geral", "Administração Pública", "Arquivologia", "Atualidades", "Auditoria", "Biologia", "Biossegurança", "Cadeia de Custódia", "Ciências", "Contabilidade", "Contabilidade Geral", "Contabilidade Pública", "Criminalística", "Criminologia", "Direito Administrativo", "Direito Ambiental", "Direito Civil", "Direito Constitucional", "Direito da Criança e do Adolescente", "Direito do Trabalho", "Direito Eleitoral", "Direito Empresarial", "Direito Financeiro", "Direito Penal", "Direito Previdenciário", "Direito Processual Civil", "Direito Processual Penal", "Direito Tributário", "Direitos Humanos", "Economia", "Estatística", "Ética no Serviço Público", "Filosofia", "Física", "Genética Forense", "Geografia", "Geografia de Goiás", "Gestão de Pessoas", "Gestão Pública", "História", "História de Goiás", "Informática", "Legislação de Trânsito", "Legislação Estadual", "Legislação Institucional", "Legislação Municipal", "Legislação Penal e Processual Especial", "Legislação Penal Extravagante", "Legislação Processual Penal Extravagante", "Lei Orgânica da Polícia Civil", "Literatura", "Língua Espanhola", "Língua Inglesa", "Língua Portuguesa", "Matemática", "Matemática Financeira", "Medicina Legal", "Noções de Administração", "Noções de Arquivologia", "Noções de Contabilidade", "Noções de Direito Administrativo", "Noções de Direito Constitucional", "Noções de Direito Penal", "Noções de Direito Processual Penal", "Noções de Economia", "Noções de Gestão Pública", "Noções de Identificação Humana", "Noções de Informática", "Noções de Segurança Pública", "Papiloscopia", "Perícia Criminal", "Primeiros Socorros", "Química", "Química Forense", "Raciocínio Lógico", "Raciocínio Lógico-Matemático", "Redação / Produção Textual", "Segurança da Informação", "Sociologia", "Tecnologia da Informação", "Toxicologia"];
const selected = new Map();
const topicDrafts = new Map();
let latest = null;
let detectedScope = null;
const slug = str => str.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
const numOrNull = id => {const v=document.getElementById(id).value.trim();return v===''?null:Number(v);};
const toggle = (id,show) => {document.getElementById(id).hidden=!show;};
function addSubject(name) {
 const trimmed=name.trim().replace(/\s+/g,' ');
 if(!trimmed)return;
 if([...selected.keys()].some(key=>slug(key)===slug(trimmed)))return;
 selected.set(trimmed,{metodo:'pdf',videoaulas:null});document.getElementById('conferido').checked=false;
 renderSelected();renderOptions();renderTopicFields();
}
function removeSubject(name){selected.delete(name);topicDrafts.delete(name);document.getElementById('conferido').checked=false;renderSelected();renderOptions();renderTopicFields();}
function renderOptions(){
 const q=slug(document.getElementById('busca-disciplina').value.trim());
 optionsBox.replaceChildren();
 const matches=catalog.filter(n=>slug(n).includes(q));
 for(const name of matches){
  const label=document.createElement('label');label.className='subject-chip';
  const cb=document.createElement('input');cb.type='checkbox';cb.checked=selected.has(name);cb.addEventListener('change',()=>cb.checked?addSubject(name):removeSubject(name));
  const span=document.createElement('span');span.textContent=name;label.append(cb,span);optionsBox.append(label);
 }
 if(!matches.length){const p=document.createElement('p');p.className='form-help';p.textContent='Nenhuma disciplina encontrada. Use o campo “Outra disciplina”.';optionsBox.append(p);}
}
function renderSelected(){
 list.replaceChildren();
 if(!selected.size){const p=document.createElement('p');p.className='form-help';p.textContent='Selecione ao menos uma matéria acima para configurar seu método.';list.append(p);return;}
 for(const [name,data] of selected){
  const row=document.createElement('div');row.className='subject-config';
  const header=document.createElement('div');header.className='subject-config-header';
  const title=document.createElement('strong');title.textContent=name;
  const remove=document.createElement('button');remove.type='button';remove.className='remove-subject';remove.textContent='Remover';remove.setAttribute('aria-label','Remover '+name);remove.addEventListener('click',()=>removeSubject(name));header.append(title,remove);
  const grid=document.createElement('div');grid.className='form-grid';
  const methodField=document.createElement('div');methodField.className='form-field';
  const methodLabel=document.createElement('label');methodLabel.textContent='Método de estudo';
  const method=document.createElement('select');method.setAttribute('aria-label','Método de estudo: '+name);
  for(const [value,text] of [['pdf','PDF'],['video','Videoaulas'],['misto','Misto (PDF + videoaulas)'],['pdf_questoes','Misto (PDF + questões)'],['questoes','Somente questões']]){const opt=document.createElement('option');opt.value=value;opt.textContent=text;method.append(opt);}
  method.value=data.metodo;method.addEventListener('change',()=>{data.metodo=method.value;document.getElementById('conferido').checked=false;renderSelected();renderTopicFields();});methodField.append(methodLabel,method);grid.append(methodField);
  if(['video','misto'].includes(data.metodo)){
   const videoField=document.createElement('div');videoField.className='form-field';const label=document.createElement('label');label.textContent='Quantidade de videoaulas (obrigatória para este método)';const input=document.createElement('input');input.type='number';input.min='1';input.max='1500';input.placeholder='Ex.: 45';input.value=data.videoaulas??'';input.setAttribute('aria-label','Videoaulas de '+name);input.addEventListener('input',()=>{data.videoaulas=input.value===''?null:Number(input.value);document.getElementById('conferido').checked=false;});videoField.append(label,input);grid.append(videoField);
  }
  const info=document.createElement('small');info.className='form-help';info.textContent= ['pdf','misto','pdf_questoes','questoes'].includes(data.metodo)?'Informe os tópicos na seção 06 ou extraia do edital com IA configurada.':data.metodo==='questoes'?'Informe os tópicos: cada bloco de questões indicará o assunto a praticar.':'Informe a quantidade de aulas para organizar o cronograma.';
  row.append(header,grid,info);list.append(row);
 }
}
document.getElementById('busca-disciplina').addEventListener('input',renderOptions);
document.getElementById('adicionar-disciplina').addEventListener('click',()=>{const input=document.getElementById('outra-disciplina');if(!input.value.trim()){input.focus();return;}addSubject(input.value);input.value='';});
document.getElementById('outra-disciplina').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();document.getElementById('adicionar-disciplina').click();}});
form.querySelectorAll('input[name="possuiArea"]').forEach(r=>r.addEventListener('change',()=>{toggle('area-box',form.elements.possuiArea.value==='sim');if(form.elements.possuiArea.value!=='sim')document.getElementById('area-especialidade').value='';document.getElementById('conferido').checked=false;detectedScope=null;document.getElementById('resultado-escopo').hidden=true;}));
document.getElementById('cargo').addEventListener('change',e=>toggle('cargo-outro-box',e.target.value==='outro'));
form.querySelectorAll('input[name="usaCursinho"]').forEach(r=>r.addEventListener('change',()=>toggle('cursinho-box',form.elements.usaCursinho.value==='sim')));
document.getElementById('simulados-opcao').addEventListener('change',e=>toggle('simulados-box',e.target.value==='sim'));
document.getElementById('redacao-opcao').addEventListener('change',e=>toggle('redacao-box',e.target.value==='sim'));
function collect(){
 const fd=new FormData(form);
 if(!selected.size)throw new Error('Selecione pelo menos uma disciplina.');
 const days=[...document.querySelectorAll('#dias input:checked')].map(el=>el.value);
 if(!days.length)throw new Error('Selecione pelo menos um dia de estudo.');
 const hours=Number(fd.get('horas')),sat=Number(fd.get('sabado')),sun=Number(fd.get('domingoHoras'));
 const weekly=days.filter(d=>!['sabado','domingo'].includes(d)).length*hours+(days.includes('sabado')?sat:0)+(days.includes('domingo')?sun:0);
 if(weekly<=0)throw new Error('Informe uma disponibilidade semanal maior que zero.');
 const names=[...selected.keys()];const seen=new Set(names.map(slug));if(seen.size!==names.length)throw new Error('Há disciplinas duplicadas.');
 for(const [name,data] of selected){if(data.videoaulas!==null&&(!Number.isInteger(data.videoaulas)||data.videoaulas<1||data.videoaulas>1500))throw new Error('Confira a quantidade de videoaulas em '+name+'.');}
 const simulados=fd.get('simuladosOpcao')==='sim';const redacao=fd.get('redacaoOpcao')==='sim';
 const quantityS=simulados?numOrNull('simulados'):null;const quantityR=redacao?numOrNull('redacao-quantidade'):null;
 if(quantityS!==null&&(!Number.isInteger(quantityS)||quantityS<1||quantityS>100))throw new Error('A quantidade de simulados deve ser de 1 a 100.');
 if(quantityR!==null&&(!Number.isInteger(quantityR)||quantityR<1||quantityR>100))throw new Error('A quantidade de redações deve ser de 1 a 100.');
 const cargo=fd.get('cargo')==='outro'?String(fd.get('cargoOutro')).trim():String(fd.get('cargo'));
 if(!cargo)throw new Error('Informe o cargo desejado.');
 const area=fd.get('possuiArea')==='sim'?String(fd.get('areaEspecialidade')||'').trim():'';
 if(fd.get('possuiArea')==='sim'&&!area)throw new Error('Informe a área ou especialidade do cargo.');
 if(detectedScope && (detectedScope.cargo!==cargo || detectedScope.area!==area))throw new Error('Cargo ou área alterados após a detecção. Execute novamente “Detectar disciplinas e tópicos com IA” antes de gerar.');
 const edital=document.getElementById('edital').files[0]??null;
 if(edital&&(!edital.name.toLowerCase().endsWith('.pdf')||edital.size>20*1024*1024))throw new Error('O edital deve ser PDF e ter até 20 MB nesta demonstração.');
 return {versao:'mvp-local-1',status:'aguardando-geracao',aluno:{nome:String(fd.get('nome')).trim()},objetivo:{concurso:String(fd.get('concurso')).trim(),cargo,area,inicio:String(fd.get('inicio')),meses:Number(fd.get('meses'))},edital:{arquivo:edital?.name??null,tamanhoBytes:edital?.size??null,conteudoExtraido:false,subtemasValidados:document.getElementById('conferido').checked},disponibilidade:{dias:days,horasDiasUteis:hours,horasSabado:sat,horasDomingo:sun,horasSemanaisEstimadas:weekly},cursinho:{utiliza:fd.get('usaCursinho')==='sim',nome:fd.get('usaCursinho')==='sim'?String(fd.get('cursinho')).trim():null},disciplinas:[...selected].map(([nome,d])=>({nome,metodo:d.metodo,quantidadeVideoaulas:['video','misto'].includes(d.metodo)?d.videoaulas:null,topicos:(topicDrafts.get(nome)||'').split('\n').map(t=>t.trim()).filter(Boolean)})),preferencias:{cicloSemanal:String(fd.get('cicloSemanal')||'tradicional'),revisoes:String(fd.get('revisoes')),simulados:{opcao:String(fd.get('simuladosOpcao')),quantidade:quantityS,frequencia:simulados?String(fd.get('simuladosFrequencia')):null},redacao:{estudarTeoria:selected.has('Redação / Produção Textual'),produzir:redacao,frequencia:redacao?String(fd.get('redacaoFrequencia')):null,quantidade:quantityR,reservarRevisao:redacao?fd.get('redacaoRevisar')==='on':false},dificuldades:String(fd.get('dificuldades')).trim(),observacoes:String(fd.get('observacoes')).trim()},aviso:'Confira os tópicos com o edital antes de gerar. No modo comercial, a geração consome um crédito da compra.'};
}
function renderTopicFields(){
 const host=document.getElementById('topicos-edital');if(!host)return;
 host.replaceChildren();
 for(const [name,data] of selected){
  if(!['pdf','misto','pdf_questoes','questoes'].includes(data.metodo))continue;
  const section=document.createElement('div');section.className='subject-config';section.dataset.subject=name;
  const label=document.createElement('label');label.textContent=name+' — tópicos do edital (um por linha)';
  const help=document.createElement('small');help.className='form-help';
  help.textContent=data.metodo==='questoes'?'Obrigatório para somente questões: informe um tópico por linha para orientar cada sessão.':'Obrigatório para métodos com PDF. Não invente subtemas.';
  const area=document.createElement('textarea');area.rows=4;area.placeholder='Ex.: Princípios fundamentais\nDireitos e garantias fundamentais';area.value=topicDrafts.get(name)||'';
  area.addEventListener('input',()=>{topicDrafts.set(name,area.value);document.getElementById('conferido').checked=false;});
  section.append(label,help,area);host.append(section);
 }
}
async function readError(resp){try{const x=await resp.json();return typeof x.detail==='string'?x.detail:JSON.stringify(x.detail);}catch{return 'Falha na requisição ('+resp.status+').';}}
const LOCAL_SERVER='http://127.0.0.1:8765/planner.html';
function friendlyFetchError(err){
 if(err instanceof TypeError || /Failed to fetch|NetworkError|Load failed/i.test(String(err?.message||''))){
  return 'Não foi possível conectar ao servidor. Confira o endereço da página e a conexão. Se estiver no computador, abra '+LOCAL_SERVER+' e mantenha o Uvicorn ativo. Se estiver em ambiente de testes hospedado, verifique o acesso e a autenticação.';
 }
 return err?.message||'Erro desconhecido.';
}
async function checkBackend(){
 const el=document.getElementById('status-servidor');if(!el)return;
 if(location.protocol==='file:'){
  el.textContent='ATENÇÃO: abra a página pelo servidor do gerador, não como arquivo local. Para testes no Windows, use '+LOCAL_SERVER+'.';
  return;
 }
 try{
  const resp=await fetch('/api/health',{cache:'no-store'});
  if(!resp.ok)throw new Error('Servidor respondeu HTTP '+resp.status);
  const info=await resp.json();
  window.PM_COMMERCIAL=info.modo==='commercial';if(window.PM_COMMERCIAL)await refreshAccess();
  el.textContent='Servidor conectado. Extração por IA: '+(info.ai_configurada?'configurada':'não configurada — cadastre GEMINI_API_KEY no arquivo .env do servidor e reinicie.');
 }catch(err){el.textContent='Servidor indisponível: '+friendlyFetchError(err);}
}

function validateStudyContent(payload){
 const missingTopics=payload.disciplinas.filter(d=>['pdf','misto','pdf_questoes','questoes'].includes(d.metodo)&&!d.topicos.length).map(d=>d.nome);
 const missingVideos=payload.disciplinas.filter(d=>['video','misto'].includes(d.metodo)&&(!Number.isInteger(d.quantidadeVideoaulas)||d.quantidadeVideoaulas<1)).map(d=>d.nome);
 const issues=[];
 if(missingTopics.length)issues.push('Informe os tópicos para os métodos com PDF ou questões: '+missingTopics.join(', ')+'.');
 if(missingVideos.length)issues.push('Informe a quantidade de videoaulas: '+missingVideos.join(', ')+'.');
 if(issues.length){
  const first=missingTopics[0]||missingVideos[0];
  const section=missingTopics.length?document.getElementById('validacao-topicos'):document.getElementById('disciplinas');
  section.scrollIntoView({behavior:'smooth',block:'start'});
  const target=missingTopics.length?[...document.querySelectorAll('#topicos-edital .subject-config')].find(el=>el.dataset.subject===first)?.querySelector('textarea'):null;
  if(target){target.setAttribute('aria-invalid','true');target.focus({preventScroll:true});}
  throw new Error(issues.join(' '));
 }
}
const generateButton=document.getElementById('gerar-pdfs');
const PM_DRAFT_KEY='pm_v26_form_draft';
const PM_JOB_KEY='pm_v26_last_job';
let pmAccess={autenticado:false,creditos:0};
let pmCheckout=null;
function pmSaveDraft(){
 try{
  const fields=[];
  for(const el of form.querySelectorAll('input,select,textarea')){
   if(!el.id && !el.name)continue;
   if(el.type==='file')continue;
   fields.push({id:el.id||null,name:el.name||null,value:el.value,checked:el.type==='checkbox'||el.type==='radio'?el.checked:null});
  }
  sessionStorage.setItem(PM_DRAFT_KEY,JSON.stringify({fields,selected:[...selected],topics:[...topicDrafts]}));
 }catch(_){/* Armazenamento indisponível: formulário atual permanece na tela. */}
}
function pmRestoreDraft(){
 try{
  const saved=JSON.parse(sessionStorage.getItem(PM_DRAFT_KEY)||'null');if(!saved)return;
  for(const item of saved.fields||[]){
   const el=item.id?document.getElementById(item.id):null;
   if(el && el.closest('#formulario') && el.type!=='file'){
    if(item.checked!==null)el.checked=item.checked;else el.value=item.value;
   }else if(item.name){
    const matches=[...form.querySelectorAll('input[name="'+CSS.escape(item.name)+'"]')];
    for(const m of matches){if(m.value===item.value && item.checked!==null)m.checked=item.checked;}
   }
  }
  selected.clear();for(const [k,v] of saved.selected||[])selected.set(k,v);
  topicDrafts.clear();for(const [k,v] of saved.topics||[])topicDrafts.set(k,v);
  renderOptions();renderSelected();renderTopicFields();
  ['cargo-outro-box','area-box','cursinho-box','simulados-box','redacao-box'].forEach(()=>{});
  toggle('cargo-outro-box',document.getElementById('cargo').value==='outro');
  toggle('area-box',form.elements.possuiArea.value==='sim');
  toggle('cursinho-box',form.elements.usaCursinho.value==='sim');
  toggle('simulados-box',document.getElementById('simulados-opcao').value==='sim');
  toggle('redacao-box',document.getElementById('redacao-opcao').value==='sim');
 }catch(_){/* Rascunho inválido é ignorado. */}
}
function pmShowAccess(message){
 const box=document.getElementById('pm-access');box.hidden=false;
 document.getElementById('pm-auth-status').textContent=message||'Entre com o e-mail da compra ou adquira seus créditos.';
 box.scrollIntoView({behavior:'smooth',block:'start'});
}
function pmSaveJob(requestId,payload){
 try{sessionStorage.setItem(PM_JOB_KEY,JSON.stringify({id:requestId,payload:JSON.stringify(payload)}));}catch(_){}
}
function pmExistingJob(payload){
 try{const last=JSON.parse(sessionStorage.getItem(PM_JOB_KEY)||'null');return last?.payload===JSON.stringify(payload)?last.id:null;}catch(_){return null;}
}
function pmDownloadBlob(blob){
 const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='POST_MORTEM_Plano_Personalizado.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
}

form.addEventListener('submit',async e=>{
 e.preventDefault();let payload;
 try{payload=collect();validateStudyContent(payload);if(!document.getElementById('conferido').checked)throw new Error('Confira e confirme os tópicos do edital antes de gerar.');}
 catch(err){document.getElementById('resultado-mensagem').textContent=err.message;result.classList.add('visible');window.alert(err.message);return;}
 latest=payload;pmSaveDraft();
 if(window.PM_COMMERCIAL && (!pmAccess.autenticado || (pmAccess.creditos<1 && !pmExistingJob(payload)))){
  pmShowAccess(pmAccess.autenticado?'Seus créditos acabaram. Compre um novo pacote para gerar outro cronograma.':'Seu formulário está preenchido. Compre créditos pela Hotmart ou entre com o e-mail da compra para gerar.');
  return;
 }
 generateButton.disabled=true;generateButton.textContent='Gerando os PDFs…';
 document.getElementById('resultado-mensagem').textContent='Preparando os arquivos no servidor…';
 result.classList.add('visible');result.scrollIntoView({behavior:'smooth',block:'nearest'});
 try{
  const requestId=window.PM_COMMERCIAL?(pmExistingJob(payload)||crypto.randomUUID().replaceAll('-','')):null;
  if(requestId)pmSaveJob(requestId,payload);
  const headers={'Content-Type':'application/json'};
  if(requestId)headers['X-PM-Request-ID']=requestId;
  const response=await fetch('/api/generate',{method:'POST',headers,credentials:'same-origin',body:JSON.stringify({perfil:payload,topicos_conferidos:true})});
  if(!response.ok){const message=await readError(response);if(message.includes('Esta tentativa falhou')||message.includes('Seu crédito foi devolvido')){try{sessionStorage.removeItem(PM_JOB_KEY);}catch(_){}}throw new Error(message);}
  const blob=await response.blob();pmDownloadBlob(blob);
  document.getElementById('resultado-mensagem').textContent='Arquivos gerados! O download do ZIP com os dois PDFs foi iniciado. Confira a pasta Downloads.';if(window.PM_COMMERCIAL)await refreshAccess();
 }catch(err){document.getElementById('resultado-mensagem').textContent='Não foi possível gerar: '+friendlyFetchError(err);}
 finally{generateButton.disabled=false;generateButton.textContent='Gerar cronograma e guia em PDF ↓';}
});
document.getElementById('detectar-disciplinas').addEventListener('click',async()=>{
 const status=document.getElementById('status-ia');const file=document.getElementById('edital').files[0];
 if(!file){status.textContent='Anexe o conteúdo programático em PDF primeiro.';return;}
 if(file.size>12*1024*1024){status.textContent='O anexo deve ter até 12 MB.';return;}
 if(selected.size && !window.confirm('A detecção automática vai acrescentar matérias e substituir tópicos das disciplinas detectadas. Deseja continuar?'))return;
 const button=document.getElementById('detectar-disciplinas');button.disabled=true;status.textContent='Detectando disciplinas e tópicos no edital…';
 try{
  const fd=new FormData(form);const cargo=fd.get('cargo')==='outro'?String(fd.get('cargoOutro')||'').trim():String(fd.get('cargo')||'');
  const area=fd.get('possuiArea')==='sim'?String(fd.get('areaEspecialidade')||'').trim():'';
  if(!cargo){status.textContent='Selecione o cargo pretendido antes da detecção.';return;}
  if(fd.get('possuiArea')==='sim'&&!area){status.textContent='Informe a área ou especialidade antes da detecção.';return;}
  const data=new FormData();data.append('edital',file);data.append('cargo',cargo);data.append('area',area);
  const response=await fetch('/api/discover',{method:'POST',body:data});if(!response.ok)throw new Error(await readError(response));
  const payload=await response.json();let count=0,subjects=0;
  for(const entry of payload.disciplinas||[]){
   if(!entry.nome||!Array.isArray(entry.topicos))continue;
   let detectedName=entry.nome;
   // Preserva exatamente o nome identificado no edital, inclusive Língua Inglesa,
   // Língua Espanhola ou Língua Estrangeira. Não inventa a escolha do candidato.
   const titles=entry.topicos.map(t=>t.texto).filter(Boolean);
   if(!titles.length)continue;
   const normalized=slug(detectedName).replace(/^(nocoes de|fundamentos de|introducao a|introducao ao) /,'');
   const existing=[...selected.keys()].find(n=>slug(n).replace(/^(nocoes de|fundamentos de|introducao a|introducao ao) /,'')===normalized);
   const name=existing||detectedName;
   if(!selected.has(name)){addSubject(name);subjects++;}
   topicDrafts.set(name,titles.join('\n'));count+=titles.length;
  }
  renderOptions();renderSelected();renderTopicFields();document.getElementById('conferido').checked=false;
  detectedScope={cargo,area};const scope=payload.escopo||{};const preview=document.getElementById('resultado-escopo');preview.hidden=false;preview.textContent='Identificação do edital: cargo '+(scope.cargo||cargo)+' | área '+(scope.area||'não informada')+' | '+(scope.modo==='comum_e_especifico'?'conteúdos comuns e específicos filtrados':'sem separação de área')+'. Confira o resultado antes de gerar.';
  const audit=payload.auditoria||{};const integrity=audit.status==='itens_numerados_conferidos'?`Conferência: ${audit.itens_extraidos} itens numerados identificados no documento, ${audit.itens_retornados} retornados. Extração literal, sem resumo da IA. `:'Conferência automática de completude indisponível neste formato; revise o edital integralmente. ';
  status.textContent=`${subjects} disciplinas adicionadas; ${count} tópicos sugeridos. ${integrity}Revise os nomes e os tópicos antes de confirmar. `+(payload.avisos||[]).join(' ');
 }catch(err){status.textContent='Detecção não concluída: '+friendlyFetchError(err)+' Se necessário, selecione manualmente.';}
 finally{button.disabled=false;}
});
form.addEventListener('reset',()=>{try{sessionStorage.removeItem(PM_DRAFT_KEY);}catch(_){}setTimeout(()=>{selected.clear();topicDrafts.clear();document.getElementById('conferido').checked=false;renderSelected();renderTopicFields();document.getElementById('busca-disciplina').value='';renderOptions();['cargo-outro-box','area-box','cursinho-box','simulados-box','redacao-box'].forEach(id=>toggle(id,false));document.getElementById('resultado-escopo').hidden=true;detectedScope=null;result.classList.remove('visible');latest=null;},0);});
document.getElementById('year').textContent=new Date().getFullYear();renderOptions();renderSelected();renderTopicFields();pmRestoreDraft();checkBackend();
form.addEventListener('input',()=>pmSaveDraft());form.addEventListener('change',()=>pmSaveDraft());
window.addEventListener('pagehide',pmSaveDraft);
(async()=>{try{const r=await fetch('/api/public-config',{cache:'no-store'});if(!r.ok)return;const data=await r.json();pmCheckout=data.checkout_url;const link=document.getElementById('pm-buy');if(pmCheckout){link.href=pmCheckout;link.hidden=false;link.addEventListener('click',pmSaveDraft);}else document.getElementById('pm-buy-unavailable').hidden=false;}catch(_){}})();


// V24: acesso individual por e-mail da compra (sessão em cookie HttpOnly).
async function refreshAccess(){
 const box=document.getElementById('pm-access');box.hidden=false;
 const resp=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'});
 if(!resp.ok)return;
 const data=await resp.json();
 box.querySelector('.pm-access-fields').hidden=!!data.autenticado;
 document.getElementById('pm-account').hidden=!data.autenticado;
 document.getElementById('pm-logout').hidden=!data.autenticado;
 document.getElementById('pm-account').textContent=data.autenticado?'Conta: '+data.email+' | Gerações disponíveis: '+data.creditos:'';
 pmAccess={autenticado:!!data.autenticado,creditos:Number(data.creditos||0)};
 const recovery=document.getElementById('pm-download-recovery');recovery.hidden=true;
 if(data.autenticado){
  try{
   const jobs=await fetch('/api/generations',{credentials:'same-origin',cache:'no-store'});
   if(jobs.ok){const info=await jobs.json();const done=(info.generations||[]).find(g=>g.status==='completed' && g.completed_at>Date.now()/1000-7*86400);
    if(done){recovery.hidden=false;recovery.dataset.jobId=done.id;}
   }
  }catch(_){}
 }
 if(!data.autenticado)document.getElementById('pm-auth-status').textContent='Preencha gratuitamente. Para gerar, compre ou entre com o e-mail da compra.';
}
document.getElementById('pm-request').addEventListener('click',async()=>{
 const status=document.getElementById('pm-auth-status');status.textContent='Solicitando código…';
 try{const resp=await fetch('/api/auth/request-code',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('pm-email').value.trim()})});const data=await resp.json();if(!resp.ok)throw Error(data.detail||'Falha ao solicitar código.');status.textContent=data.message;}
 catch(e){status.textContent=e.message;}
});
document.getElementById('pm-login').addEventListener('click',async()=>{
 const status=document.getElementById('pm-auth-status');status.textContent='Validando código…';
 try{const resp=await fetch('/api/auth/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('pm-email').value.trim(),code:document.getElementById('pm-code').value.trim()})});const data=await resp.json();if(!resp.ok)throw Error(data.detail||'Falha no acesso.');status.textContent='Acesso autorizado.';await refreshAccess();}
 catch(e){status.textContent=e.message;}
});
document.getElementById('pm-logout').addEventListener('click',async()=>{await fetch('/api/auth/logout',{method:'POST'});await refreshAccess();});

document.getElementById('pm-recover').addEventListener('click',async e=>{
 e.preventDefault();const msg=document.getElementById('pm-auth-status');
 try{
  const id=document.getElementById('pm-download-recovery').dataset.jobId;if(!id)throw Error('Nenhuma geração disponível.');
  msg.textContent='Recuperando o arquivo…';
  const resp=await fetch('/api/generations/'+id+'/download',{credentials:'same-origin',cache:'no-store'});
  if(!resp.ok)throw Error(await readError(resp));pmDownloadBlob(await resp.blob());msg.textContent='Download iniciado novamente, sem consumir crédito.';
 }catch(err){msg.textContent=friendlyFetchError(err);}
});
