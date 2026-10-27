const products = window.POST_MORTEM_PRODUTOS || [];
const container = document.getElementById('products');
const dialog = document.getElementById('product-dialog');
const content = document.getElementById('dialog-content');
let opener;
function el(tag, className, text) {
 const node = document.createElement(tag); if(className) node.className = className;
 if(text !== undefined) node.textContent = text; return node;
}
function priceLabel(product) {
 const amount = product.preco;
 return typeof amount === 'number' && Number.isFinite(amount) && amount >= 0
  ? el('p','product-price',amount === 0 ? 'Gratuito' : amount.toLocaleString('pt-BR',{style:'currency',currency:'BRL'}))
  : el('p','product-price pending','Valor a confirmar');
}
function purchase(product) {
 const url = new URL(product.link);
 if(url.protocol !== 'https:' || !['pay.hotmart.com','hotmart.com'].includes(url.hostname)) throw new Error('Link Hotmart inválido');
 const a = el('a','button gold',product.preco === 0 ? 'Acessar gratuitamente ↗' : 'Comprar na Hotmart ↗');
 a.href=url.href; a.target='_blank'; a.rel='noopener noreferrer';
 a.setAttribute('aria-label', `${product.nome}: abrir Hotmart em nova aba`);return a;
}
function openDetails(product, button) {
 opener=button; content.replaceChildren();
 const grid=el('div','detail-grid'); const images=el('div','detail-images');
 for(const [i,path] of product.galeria.entries()) {
  const img=el('img'); img.src=path; img.alt=`Arte de apresentação de ${product.nome}${i ? ': guia de utilização' : ''}`; images.append(img);
 }
 const info=el('div','detail-info'); info.append(el('p','eyebrow',product.categoria));
 const h=el('h2','',product.nome);h.id='dialog-title';info.append(h,priceLabel(product),el('p','detail-description',product.descricao),el('h3','','Para quem é'),el('p','',product.publico),el('h3','','O que o material apresenta'));
 const list=el('ul','content-list'); for(const line of product.conteudo) list.append(el('li','',line));info.append(list);
 if(product.aviso)info.append(el('p','notice',product.aviso));
 if(product.parcelamento) info.append(el('p','installments',product.parcelamento + ' · parcelamento sujeito às condições do checkout'));
 info.append(purchase(product),el('p','fine-print',product.preco === 0 ? 'Material gratuito. O acesso pode exigir cadastro no Hotmart Club.' : 'Preço à vista informado pela POST MORTEM. Confirme o total e as condições no checkout da Hotmart.')); 
 grid.append(images,info);content.append(grid,el('p','preview-note','Prévia das artes de divulgação fornecidas pela marca. Não corresponde a uma amostra integral do conteúdo.'));
 dialog.showModal();
}
for(const product of products) {
 const card=el('article','product');card.dataset.kind=product.categoria.includes('FLASHCARDS')?'flashcards':'guia';const visual=el('button','product-visual');visual.type='button';visual.setAttribute('aria-label',`Conhecer ${product.nome}`);
 const img=el('img'); img.src=product.imagem;img.alt=`Capa de ${product.nome}`;img.loading='lazy';img.width=1254;img.height=1254;img.addEventListener('error',()=>{if(!img.dataset.fallback){img.dataset.fallback='1';img.src='assets/logo-post-mortem.jpeg';img.alt='Identidade visual POST MORTEM — capa indisponível';}});visual.append(img);
 const body=el('div','product-body');body.append(el('p','eyebrow',product.categoria),el('h3','',product.nome),el('p','product-description',product.descricao),priceLabel(product));
 if(product.parcelamento)body.append(el('p','installments',product.parcelamento));
 const actions=el('div','product-actions');const details=el('button','button outline','Conhecer o conteúdo');details.type='button';
 details.addEventListener('click',()=>openDetails(product,details));visual.addEventListener('click',()=>openDetails(product,visual));actions.append(details,purchase(product));body.append(actions);card.append(visual,body);container.append(card);
}
document.querySelector('.close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left || event.clientX>r.right || event.clientY<r.top || event.clientY>r.bottom)dialog.close();}});
dialog.addEventListener('close',()=>opener?.focus());
document.getElementById('year').textContent=new Date().getFullYear();

// Filtros acessíveis, sem ocultar informações de preço ou condições.
const filters=document.querySelectorAll('[data-filter]');
for(const filter of filters){
 filter.addEventListener('click',()=>{
  const value=filter.dataset.filter;let shown=0;
  for(const card of container.querySelectorAll('.product')){
   const match=value==='todos'||card.dataset.kind===value;card.hidden=!match;if(match)shown++;
  }
  for(const item of filters){const active=item===filter;item.classList.toggle('active',active);item.setAttribute('aria-pressed',String(active));}
  document.getElementById('filter-status').textContent=`${shown} materiais exibidos.`;
 });
}


// Interação editorial e descoberta de materiais — sem recomendações comerciais disfarçadas.
const recommendations={
 comecar:{title:'Comece pela organização',body:'O guia Do Zero à Preparação Policial ajuda a estruturar rotina, edital e método de estudo.',product:'Do Zero à Preparação Policial'},
 entender:{title:'Aprofunde com exemplos',body:'Explore os e-books interativos. Cadeia de Custódia é direcionado a concursos policiais; A Morte pela Ciência é gratuito e introdutório.',product:'Dissecando a Cadeia de Custódia'},
 revisar:{title:'Pratique a recuperação ativa',body:'As coleções de flashcards Anki permitem revisar Teoria do Crime e Crimes contra a Administração Pública.',product:'Flashcards'}
};
const result=document.getElementById('discovery-result');
for(const choice of document.querySelectorAll('[data-goal]')){
 choice.addEventListener('click',()=>{
  for(const c of document.querySelectorAll('[data-goal]'))c.setAttribute('aria-pressed',String(c===choice));
  const r=recommendations[choice.dataset.goal];result.replaceChildren();
  const box=document.createElement('div'),heading=document.createElement('strong'),p=document.createElement('p'),button=document.createElement('button');
  heading.textContent=r.title;p.textContent=r.body;box.append(heading,p);
  button.type='button';button.className='button gold';button.textContent='Ver materiais sugeridos ↗';
  button.addEventListener('click',()=>{
    const filter=choice.dataset.goal==='revisar'?'flashcards':choice.dataset.goal==='entender'?'guia':'todos';
    document.querySelector(`[data-filter="${filter}"]`)?.click();
    document.getElementById('materiais').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  });
  result.append(box,button);result.hidden=false;
 });
}
const progress=document.getElementById('scroll-progress-fill');
function updateProgress(){const d=document.documentElement;const max=d.scrollHeight-d.clientHeight;progress.style.width=(max>0?Math.max(0,Math.min(100,window.scrollY/max*100)):0)+'%';}
window.addEventListener('scroll',updateProgress,{passive:true});window.addEventListener('resize',updateProgress);updateProgress();
if('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
 const observer=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){e.target.classList.add('in-view');observer.unobserve(e.target)}},{threshold:.08});
 for(const node of document.querySelectorAll('.section-heading,.credibility-grid article,.steps li')){node.classList.add('reveal');observer.observe(node)}
}
