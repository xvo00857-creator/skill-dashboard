import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const root = new URL('../site/', import.meta.url);
const html = readFileSync(new URL('index.html', root), 'utf8');
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {value:'',innerHTML:'',textContent:'',hidden:false});
  return elements.get(id);
};
const buttons = ['', 'doubao', 'workbuddy', 'tie', 'uncompared'].map(value => ({
  dataset:{comparison:value}, setAttribute(key,value){this[key]=value;}
}));
const context = vm.createContext({window:{},document:{
  querySelector:element,
  querySelectorAll(selector){
    if(selector==='.comparison-filters button')return buttons;
    if(selector==='.filters input,.filters select')return ['search','focusDirection','priority','scoreBand','category','source'].map(id=>element('#'+id));
    return [];
  }
}});
for (const file of ['catalog-data.js','workbuddy-card-data.js','provider-evaluation-data.js']) {
  vm.runInContext(readFileSync(new URL(file,root),'utf8'),context,{filename:file});
}
for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInContext(match[1],context);
const run = code => vm.runInContext(code,context);
const total = run('ITEMS.length');
assert.equal(element('#countline').textContent,`共 ${total} 个结果 · 当前显示 ${Math.min(72,total)} 个`);
const groups = {};
for(const button of buttons.slice(1)){
  button.onclick();
  const key=button.dataset.comparison;
  const expected=run(`ITEMS.filter(x=>(skillVerdict(x.row)?.key||'uncompared')===${JSON.stringify(key)}).length`);
  groups[key]=expected;
  assert.equal(element('#countline').textContent,`共 ${expected} 个结果 · 当前显示 ${Math.min(72,expected)} 个`);
  assert.equal(button['aria-pressed'],'true');
  assert.equal(buttons.filter(x=>x['aria-pressed']==='true').length,1);
  element('#loadMore').onclick();
  assert.equal(element('#countline').textContent,`共 ${expected} 个结果 · 当前显示 ${Math.min(144,expected)} 个`);
}
assert.equal(Object.values(groups).reduce((a,b)=>a+b,0),total);
buttons[1].onclick();
element('#scoreBand').value='strong';
element('#scoreBand').oninput();
const combined=run("ITEMS.filter(x=>skillVerdict(x.row)?.key==='doubao'&&scoreMatches(x,'strong')).length");
assert.equal(element('#countline').textContent,`共 ${combined} 个结果 · 当前显示 ${Math.min(72,combined)} 个`);
element('#search').value='___no_matching_skill_392854___';
element('#search').oninput();
assert.equal(element('#countline').textContent,'共 0 个结果 · 当前显示 0 个');
assert.equal(element('#allgrid').innerHTML,'<div class="empty">没有匹配结果</div>');
assert.equal(element('#loadMore').hidden,true);
element('#search').value='';
element('#scoreBand').value='';
buttons[0].onclick();
assert.equal(element('#countline').textContent,`共 ${total} 个结果 · 当前显示 ${Math.min(72,total)} 个`);
// Compare-filter must reuse the existing verdict keys, not redefine score thresholds.
assert.equal(run('scoreVerdict(10,8).key'),'tie');
assert.equal(run('scoreVerdict(10,7.9).key'),'doubao');
assert.equal(run('scoreVerdict(7,10).key'),'workbuddy');
assert.equal(run('scoreVerdict(null,10)'),null);
console.log(JSON.stringify({passed:true,total,groups,checks:['all verdict groups','pagination','combined score filter','empty results','reset','unchanged tie threshold']}));
