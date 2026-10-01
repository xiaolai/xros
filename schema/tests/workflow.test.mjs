import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const doc=readFileSync(new URL('../../claude/commands/run.md',import.meta.url),'utf8');
const body=doc.split('```js\n')[1].split('\n```')[0];
const code=body.slice(body.indexOf('const spec = args'));
const run=new (Object.getPrototypeOf(async function(){}).constructor)('args','agent','parallel','budget','phase','log',code);
const spec=JSON.parse(readFileSync(new URL('../examples/lock-free-queue.spec.json',import.meta.url)));
spec.stopping={minRounds:1,maxRounds:1,budgetTokens:100000};
spec.search.maxConcurrentAgents=3;
function agentMock(cancel=false){return async (_prompt,opts)=>{
 if(opts.label.startsWith('refute:')) {if(cancel && opts.label.endsWith('.0')) throw new Error('cancelled'); return {refuted:false,reason:'valid',triggeredChecklist:[]};}
 return {producedArtifact:true,claimsComplete:true,artifactFiles:[{path:'answer.json',content:'4'}],selfIdentifiedGaps:[],summary:'four'};
};}
const parallel=async tasks=>JSON.parse(JSON.stringify(await Promise.all(tasks.map(f=>f()))));
test('serialized parallel verdicts survive and bind to their assigned candidate',async()=>{
 const out=await run(structuredClone(spec),agentMock(),parallel,{spent:()=>0},()=>{},()=>{});
 assert.equal(out.ranked.length,spec.search.approaches.length);
 assert.ok(out.ranked.every(c=>c.verdicts.length===3));
});
test('cancelled vote fails closed and retry state remains serializable',async()=>{
 const out=await run(structuredClone(spec),agentMock(true),parallel,{spent:()=>0},()=>{},()=>{});
 assert.equal(out.ranked.length,0);
 assert.ok(Object.values(out.routeState).every(s=>!s.blocked));
 assert.doesNotThrow(()=>JSON.stringify(out));
});

test('an interrupted vote can recover with the same candidate on the next round',async()=>{
 const first=await run(structuredClone(spec),agentMock(true),parallel,{spent:()=>0},()=>{},()=>{});
 const retry={...structuredClone(spec),stopping:{...spec.stopping,maxRounds:2},priorRounds:first.rounds,priorSeen:first.seenKeys,priorRouteState:first.routeState,priorDry:first.dry,priorInfoSeq:first.infoSeq,priorIdeas:first.priorIdeas,priorCounterexamples:first.counterexamples};
 const second=await run(retry,agentMock(),parallel,{spent:()=>0},()=>{},()=>{});
 assert.equal(second.rounds,2);assert.equal(second.ranked.length,spec.search.approaches.length);
});
