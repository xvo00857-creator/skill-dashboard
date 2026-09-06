import assert from 'node:assert/strict';
import {readFileSync,existsSync,statSync} from 'node:fs';
import vm from 'node:vm';
const root=new URL('../site/',import.meta.url);
const context=vm.createContext({window:{}});
vm.runInContext(readFileSync(new URL('catalog-data.js',root),'utf8'),context);
const data=context.window.SKILL_ITEMS;
const summary=JSON.parse(readFileSync(new URL('sync-summary.json',root)));
assert.equal(data.length,summary.counts.skills);
assert.equal(new Set(data.map(x=>x.row)).size,summary.counts.skills);
assert.equal(summary.has_more,false);
assert(Number.isInteger(summary.sourceRevision)&&summary.sourceRevision>0);
assert.equal(data.reduce((n,x)=>n+x.tested,0),summary.counts.real_links);
for(const item of data){
  assert.equal(item.cases.length,3);
  assert.equal(item.tested,item.cases.filter(c=>c.url).length);
  if(item.historicalScore!=null){assert.equal(item.score,null);assert.match(item.scoreNote,/未核实/);}
  for(const c of item.cases){
    assert(!c.url||/^https?:\/\/(?:www\.)?doubao\.com\/(?:thread|chat)\//.test(c.url));
    if(c.preparedPrompt)assert(c.revisionNote);
    if(c.executionStatus==='runner_timeout')assert.match(c.evidenceNote,/超时/);
    if(c.lastAttempt?.status==='runner_timeout')assert.match(c.lastAttempt.label,/未确认完成/);
    assert(!c.url.includes('api5-normal'));
  }
}
assert.equal(summary.counts.last_batch_attempts,16);
const case1332=data.find(x=>x.row===1332).cases[0];
assert.equal(case1332.url,'');
assert.equal(case1332.lastAttempt.status,'completed');
assert(case1332.lastAttempt.answer.length>0);
assert.match(readFileSync(new URL('index.html',root),'utf8'),/caseEvidenceHtml\(c\)/);
const archives=data.flatMap(x=>x.cases.flatMap(c=>c.archivedDeliverables||[]));
assert.equal(archives.length,232);
const files=archives.flatMap(x=>x.files);
assert.equal(files.length,summary.localArtifacts.files);
for(const file of files){
  assert(file.url.startsWith('assets/run-archive/'));
  const path=new URL(file.url,root);
  assert(existsSync(path));assert(statSync(path).size<100_000_000);
}
console.log(JSON.stringify({passed:true,skills:data.length,links:summary.counts.real_links,checks:['unique identities','complete source capture','real links only','timeout not success','latest 16 attempts','prompt version notes','stale grade held']}));
