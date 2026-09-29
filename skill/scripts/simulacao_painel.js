const fs=require('fs'),vm=require('vm');
const [html,cenario]=[fs.readFileSync(process.argv[1],'utf8'),JSON.parse(process.argv[2])];
const script=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
class El{
  constructor(tag,svg){this.tag=tag;this._svg=!!svg;this.attrs={};this.children=[];this._html='';this.textContent='';this.hidden=false;
    this.className='';this.style={setProperty(){}};this.dataset={};this.onclick=null;this.clicks=[];this._first=null;this.value='';this.parentNode=null}
  set innerHTML(v){this._html=String(v);for(const c of this.children)c.parentNode=null;this.children=[];this._first=null}
  get innerHTML(){return this._html}
  get tagName(){return this._svg?this.tag:this.tag.toUpperCase()}
  get firstChild(){return this.children[0]||(this._first=this._first||new El('?'))}
  get firstElementChild(){return this.firstChild}
  get nextSibling(){const p=this.parentNode;return p&&p.children[p.children.indexOf(this)+1]||null}
  get attributes(){return Object.entries(this.attrs).map(([name,value])=>({name,value}))}
  _adota(c){if(c.parentNode)c.remove();c.parentNode=this;return c}
  append(...c){for(const x of c)this.children.push(this._adota(x))}
  appendChild(c){this.children.push(this._adota(c));return c}
  insertBefore(c,ref){this._adota(c);const i=ref?this.children.indexOf(ref):-1;
    if(i<0)this.children.push(c);else this.children.splice(i,0,c);return c}
  remove(){const p=this.parentNode;if(p){const i=p.children.indexOf(this);if(i>=0)p.children.splice(i,1)}this.parentNode=null}
  cloneNode(){const c=new El(this.tag,this._svg);Object.assign(c.attrs,this.attrs);return c}
  insertAdjacentHTML(pos,h){this._html+=h}
  setAttribute(k,v){this.attrs[k]=String(v)}
  getAttribute(k){return k in this.attrs?this.attrs[k]:null}
  hasAttribute(k){return k in this.attrs}
  removeAttribute(k){delete this.attrs[k]}
  toggleAttribute(k,f){const on=f===undefined?!(k in this.attrs):!!f;if(on)this.attrs[k]=this.attrs[k]??'';else delete this.attrs[k];return on}
  addEventListener(t,f){if(t==='click')this.clicks.push(f)}
  querySelector(){return this.firstChild}
  querySelectorAll(){return []}
  get classList(){return{add(){},remove(){},toggle(){},contains(){return false}}}
  closest(){return new El('div')}
  after(){} before(){} scrollIntoView(){} getBoundingClientRect(){return{}}
  get outer(){const a=Object.entries(this.attrs).map(([k,v])=>` ${k}="${v}"`).join('');
    const d=Object.entries(this.dataset).map(([k,v])=>` data-${k}="${v}"`).join('');
    return `<${this.tag}${a}${d}>${this._html}${this.children.map(c=>c.outer).join('')}${this.textContent}</${this.tag}>`}
  get outerHTML(){return this.outer}
}
const ids={};
const document={getElementById:id=>ids[id]||(ids[id]=new El('div')),createElement:t=>new El(t),createElementNS:(n,t)=>new El(t,true),
  querySelector:()=>new El('div'),querySelectorAll:()=>[],body:new El('body'),title:'',addEventListener(){}};
const nada=()=>0;
const ctx={document,fetch:()=>new Promise(()=>{}),setInterval:nada,setTimeout:nada,clearInterval:nada,clearTimeout:nada,
  marked:{parse:s=>s},console,localStorage:{getItem:()=>null,setItem(){}},
  matchMedia:()=>({matches:false,addEventListener(){}}),getComputedStyle:()=>({getPropertyValue:()=>''}),
  navigator:{},location:{href:''},open(){}};
ctx.window=ctx;vm.createContext(ctx);
vm.runInContext(script,ctx);
const $=id=>document.getElementById(id);
if(cenario.modo==='render'){
  vm.runInContext(`D=${JSON.stringify(cenario.D)};render()`,ctx);
  const out={raf:vm.runInContext('typeof requestAnimationFrame',ctx),caf:vm.runInContext('typeof cancelAnimationFrame',ctx),ids:{}};
  for(const id of cenario.ids){const c=$(id).children;out.ids[id]={n:c.length,filhos:c.map(x=>x.outer)}}
  process.stdout.write(JSON.stringify(out));
}else{
vm.runInContext(`D=${JSON.stringify(cenario.D)};escolhida=${JSON.stringify(cenario.escolhida)};aberto=${JSON.stringify(cenario.aberto)};rodada(D.rodada)`,ctx);
const lis=$('fases').children;
const out={cab:$('rodada-cab').textContent,aviso_oculto:$('rodada-aviso').hidden,cols_ocultas:$('rodada-cols').hidden,
  fases:lis.map(li=>({classe:li.className||li.attrs.class||'',html:li.outer}))};
if(cenario.clicar){
  const li=lis.find(l=>l.outer.includes(`data-doc="${cenario.clicar}"`));
  if(li){const b=li.children[0]||li._first;const fs=[b&&b.onclick,...(b?b.clicks:[]),li.onclick,...li.clicks].filter(Boolean);
    const ev={target:b,currentTarget:b,preventDefault(){},stopPropagation(){}};
    for(const f of fs){try{f(ev)}catch(e){}}}
  out.doc_cab=$('trilha-cab').textContent;
}
process.stdout.write(JSON.stringify(out));
}
