"""Offline evidence-preserving refresh. Never dispatches, grades or creates shares.

Inputs are ignored, locally captured snapshots; only whitelisted fields enter site.
Run once per capture against the saved previous catalog, not a moving baseline.
"""
import collections
import copy
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from prepare_public import clean

REAL = re.compile(r'https?://(?:www\.)?doubao\.com/(?:thread|chat)/[^\s"<>\\]+')
HTTP = re.compile(r'https?://[^\s"<>\\`\[\]（）。，；]+')
STATUS = {'runner_timeout':'执行超时，未确认完成', 'completed':'执行结束，尚需核对产物',
 'public_share_unverified':'已存对话链接，分享可访问性未复核',
 'completed_missing_artifact':'执行结束但缺少产物', 'runner_dispatch_failed':'提交失败',
 'runner_stalled':'执行停滞', 'interaction_required':'等待交互，未完成',
 'input_missing_business_attachment':'缺少业务附件', 'input_missing':'缺少输入'}

def load(path):
    return json.loads(Path(path).read_text())

def load_js(path):
    return json.loads(Path(path).read_text().split('=',1)[1].strip().rstrip(';'))

def clean_tree(value):
    # Sanitize decoded strings before JSON escaping can hide quote delimiters.
    if isinstance(value,str):return clean(value.encode('utf8'),'captured-text').decode('utf8')
    if isinstance(value,list):return [clean_tree(x) for x in value]
    if isinstance(value,dict):return {k:clean_tree(v) for k,v in value.items()}
    return value

def cell(row, col):
    return str(row.get(col,{}).get('value','') or '')

def urls(row,col,pattern=HTTP):
    c=row.get(col,{})
    values=[v.get('link','') for v in c.get('rich_text',[]) if isinstance(v,dict)]
    values += pattern.findall(cell(row,col))
    return list(dict.fromkeys(u.rstrip('。；,;）)') for u in values if pattern.fullmatch(u)))

def key(url):
    # www and scheme differences do not identify a new conversation.
    p=urlsplit(url)
    return p.netloc.removeprefix('www.')+p.path.rstrip('/') if url else ''

def score(value):
    s=str(value).strip()
    if not re.fullmatch(r'(?:10(?:\.0+)?|[0-9](?:\.\d+)?)(?:\s*/\s*10)?',s):return None
    return float(s.split('/')[0])

def artifact_bundle(links):
    links=list(dict.fromkeys(u for u in links if HTTP.fullmatch(u) and not re.search(r'redacted|%3c|file://',u,re.I)))
    if not links:return None
    images=[]; files=[]
    for i,u in enumerate(links):
        try:
            parsed=urlsplit(u)
            if not re.fullmatch(r'[A-Za-z0-9.-]+(?::[0-9]+)?',parsed.netloc):continue
            if parsed.hostname in {'example.com','example.org','localhost'}:continue
            suffix=Path(parsed.path).suffix.lower()
        except ValueError:continue
        if suffix in {'.png','.jpg','.jpeg','.webp','.gif'}:images.append(u)
        elif suffix in {'.pdf','.docx','.pptx','.xlsx','.zip','.md','.csv','.html','.txt','.mp4'} or re.search(r'/(?:file|docx|slides|sheets)/',parsed.path):
            files.append({'url':u,'title':f'表格结果链接 {i+1}（未重新验收）','suffix':suffix.lstrip('.').upper() or 'FILE'})
    if not images and not files:return None
    return {'kind':'bundle','title':'本次产物','images':images,'files':files}

def archived_answer(run):
    try:
        d=load(Path(run['root'])/'run_summary.json')
        rd=[v for lane in d.get('lanes',[]) for v in lane.get('rounds',[])][-1]
        return str((rd.get('completion',{}).get('selected') or {}).get('text','') or '')
    except (OSError,ValueError,IndexError):return ''

def refresh(snapshot, previous, runs):
    assert snapshot['has_more'] is False
    assert len(snapshot['rows']) >= 2
    old={x['row']:x for x in previous}
    byurl={}; latest={}; knownshares={}
    for run in sorted(runs,key=lambda x:x['mtime']):
        identity=(int(run['row']),run['case'])
        if run['status']!='dry_run':latest[identity]=run
        if REAL.fullmatch(run['url'] or ''):
            byurl[(identity,key(run['url']))]=run
            knownshares[identity]=run
    items=[]; counts=collections.Counter(); details=[]
    for rn,row in snapshot['rows'].items():
        if rn=='1':continue
        rn=int(rn); base=copy.deepcopy(old.get(rn,{})); name=cell(row,'B')
        assert not base or base['name']==name, f'Skill identity changed at row {rn}'
        mark=cell(row,'AM').strip(); sc=score(cell(row,'O'))
        item={**base,'row':rn,'name':name,'category':cell(row,'C') or '待分类',
          'description':cell(row,'D') or '暂无用途说明','focusDirection':cell(row,'AW') or '其他低优先级方向',
          'source':cell(row,'AX') or 'GitHub','mark':mark,'isP0':mark.upper()=='P0',
          'isP1':mark.upper()=='P1','isP2':mark.upper()=='P2',
          'sourceUrl':next(iter(urls(row,'A')),''),'xhsUrl':next(iter(urls(row,'AP')),''),
          'zipUrl':next(iter(urls(row,'E')),''),'score':sc,'scoreLabel':f'{sc:.1f}' if sc is not None else cell(row,'O') or '未评分',
          'conclusion':cell(row,'AJ'),'sheetStatus':cell(row,'W'),'lastTestAt':cell(row,'AK'),'cases':[]}
        result_changed=False
        for n,(pc,lc,ac) in enumerate(zip(['I','K','M'],['X','Z','AB'],['Y','AA','AC']),1):
            prior=next((c for c in base.get('cases',[]) if c['number']==n),{})
            current_prompt=cell(row,pc); u=next(iter(urls(row,lc,REAL)),'')
            identity=(rn,n)
            if not u:
                known=knownshares.get(identity)
                if known and known['name']==name:
                    u=known['url'];counts['archived_links_not_in_sheet']+=1
                elif REAL.fullmatch(prior.get('url','')):u=prior['url']
            matching=byurl.get((identity,key(u)))
            if matching and matching['name']!=name:matching=None
            same=bool(u and key(u)==key(prior.get('url','')))
            changed=bool(u and not same)
            result_changed |= changed
            answer=cell(row,ac)
            if not answer and same:answer=prior.get('answer','')
            if not answer and matching:answer=archived_answer(matching)
            prompt=matching.get('prompt','') if matching else ''
            prompt_basis='执行归档' if prompt else ''
            if not prompt and same:
                prompt=prior.get('prompt','');prompt_basis='原看板记录，未重新验证'
            if not prompt:
                prompt=current_prompt;prompt_basis='表格当前版本；与本次执行版本的对应关系未核实' if u else '当前待执行题目'
            note=''
            if current_prompt and prompt!=current_prompt:
                note='Prompt 后续已改写，本页先保留本次结果对应的历史题目；新版未据此认定已重测。'
                counts['prompt_version_notes']+=1
            status=matching['status'] if matching else ('recorded' if u else 'not_run')
            evidence_note=STATUS.get(status,'已收录对话和表格结果，未重新验收' if u else '暂无真实对话链接')
            artifact=prior.get('artifact') if same else None
            attached=artifact_bundle([v for v in urls(row,ac) if not REAL.fullmatch(v)])
            if attached and (not same or not artifact):artifact=attached
            structured=[]
            if matching:
                for a in matching.get('artifacts',[]):
                    if isinstance(a,dict):
                        v=next((a.get(k) for k in ['url','uri','location'] if HTTP.fullmatch(str(a.get(k,'')))),'')
                        if v and not REAL.fullmatch(v):structured.append(v)
            captured=artifact_bundle(structured)
            if not artifact and captured:artifact=captured
            # The result cell can be plain prose, not necessarily an attachment.
            c={'number':n,'prompt':prompt,'promptBasis':prompt_basis,'preparedPrompt':current_prompt if note else '',
               'revisionNote':note,'answer':answer,'url':u,'tested':bool(u),'artifact':artifact,
               'executionStatus':status,'evidenceNote':evidence_note}
            if prior.get('archivedDeliverables'):
                c['archivedDeliverables']=prior['archivedDeliverables']
            if changed and prior.get('url'):c['previousResultUrl']=prior['url']
            last=latest.get(identity)
            if last and last['name']==name and (not matching or last['mtime']>matching['mtime']) and (not last['url'] or key(last['url'])!=key(u)):
                # An unfinished newer attempt must not erase a previously captured result.
                c['lastAttempt']={'status':last['status'],'label':STATUS.get(last['status'],last['status']),
                  'finishedAt':last['finished'],'prompt':last['prompt'],
                  'answer':archived_answer(last),'url':last['url'] if REAL.fullmatch(last['url'] or '') else '',
                  'note':'较新执行记录；未取得可对应的公开分享链接，不替代上方历史结果。'}
                counts['later_attempts']+=1
                if 'resume_ask_on_risk' in last['root']:counts['last_batch_attempts']+=1
            if not u and last and last['name']==name:
                c['executionStatus']=last['status'];c['evidenceNote']=STATUS.get(last['status'],last['status'])
                if not c['answer']:c['answer']=archived_answer(last)
                if last['prompt']:
                    c['prompt']=last['prompt'];c['promptBasis']='执行归档（历史题目）'
                    if current_prompt and current_prompt!=last['prompt']:
                        if not c['revisionNote']:counts['prompt_version_notes']+=1
                        c['preparedPrompt']=current_prompt
                        c['revisionNote']='此处展示暂停前实际执行的历史题目；后续改写版本保留在下方，尚未据此认定重测。'
            if changed:counts['new_or_replaced_case_links']+=1
            if answer!=prior.get('answer',''):counts['changed_answer_cells']+=1
            if u and not prior.get('url'):counts['new_link_slots']+=1
            item['cases'].append(c)
        # Scores are not recomputed during synchronization. A changed result cannot
        # silently inherit a numeric grade without evidence of matching provenance.
        if result_changed and sc is not None:
            item['historicalScore']=sc;item['score']=None;item['scoreLabel']='待复核（结果已更新）'
            item['scoreNote']='表格保留的分数未核实是否对应新结果；本次未重新评分。'
            counts['scores_held_for_provenance']+=1
        elif base.get('historicalScore') is not None:
            item['historicalScore']=base['historicalScore'];item['score']=None
            item['scoreLabel']=base.get('scoreLabel','待复核（结果已更新）')
            item['scoreNote']=base.get('scoreNote','表格保留的分数未核实是否对应新结果；本次未重新评分。')
        item['tested']=sum(c['tested'] for c in item['cases'])
        item['testStatus']=f"已收录 {item['tested']}/3 条真实对话；链接数量不代表执行成功"
        item['risk']=item['score'] is not None and item['score']<6
        if not item['conclusion']:item['conclusion']=item['testStatus']+'；'+(item['sheetStatus'] or '待核对结果与产物')
        if rn not in old:counts['new_skill_cards']+=1
        items.append(item)
    items.sort(key=lambda x:(0 if x['isP0'] else 1 if x['isP1'] else 2 if x['isP2'] else 3,x['risk'],-(x['score'] if x['score'] is not None else -1),x['row']))
    counts['skills']=len(items);counts['real_links']=sum(x['tested'] for x in items)
    counts['three_link_skills']=sum(x['tested']==3 for x in items)
    counts['zero_link_skills']=sum(x['tested']==0 for x in items)
    return items,dict(counts)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture',type=Path)
    parser.add_argument('--updated-at',default='2026-09-06')
    args=parser.parse_args()
    repo=Path(__file__).resolve().parents[1]
    capture=(args.capture or repo/'.publish-local/refresh-20260903').resolve()
    previous=capture/'previous-catalog.json'
    if not previous.exists():previous.write_text(json.dumps(load_js(repo/'site/catalog-data.js'),ensure_ascii=False))
    snapshot=load(capture/'sheet-cells.json')
    items,counts=refresh(snapshot,load(previous),load(capture/'run-inventory.json'))
    encoded=('window.SKILL_ITEMS='+json.dumps(clean_tree(items),ensure_ascii=False,separators=(',',':'))+';\n').encode()
    (repo/'site/catalog-data.js').write_bytes(clean(encoded,'catalog-data.js'))
    previous_summary=load(repo/'site/sync-summary.json')
    summary={'updatedAt':args.updated_at,'executionCutoff':args.updated_at+'（截至本次已核验归档）',
        'sourceRevision':snapshot['revision'],'has_more':False,'counts':counts,
        'workbuddyCases':1122,'notes':['只同步已有结果，未启动测试或评分','链接数量不代表成功数量','无分享链接的最后一轮结果单独标注']}
    if previous_summary.get('localArtifacts',{}).get('files',0)>0:
        summary['localArtifacts']=previous_summary['localArtifacts']
    else:
        archives=[a for item in items for case in item.get('cases',[]) for a in case.get('archivedDeliverables',[])]
        files=[f for archive in archives for f in archive.get('files',[])]
        summary['localArtifacts']={
            'files':len(files),
            'cases':len(archives),
            'bytes':sum((repo/'site'/f['url']).stat().st_size for f in files if (repo/'site'/f['url']).exists()),
            'note':'本地已有附件按归档执行单独展示；未将旧版本产物冒充最新结果。'
        }
    (repo/'site/sync-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
