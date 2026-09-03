"""Copy manifest-verified deliverables only; never execute their contents.
Unmatched/newer conversations never inherit older generated files.
Usage: python3 tools/merge_local_artifacts.py /archive/popular-skills.../runs/today.../download-manifest-network.json
"""
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import quote
from prepare_public import clean
from audit_public import audit
from merge_snapshot import load_js, load, clean_tree

def main():
    repo=Path(__file__).resolve().parents[1]
    manifest=Path(sys.argv[1]).resolve(); batch=manifest.parent
    data=load(manifest)
    source_dir=batch/'downloaded-artifacts-network'
    initial=audit(source_dir)
    blocked={'symlink','archive_depth_limit','archive_size_limit','encrypted_archive','github_file_size'}
    assert not [f for f in initial['findings'] if f['rule'] in blocked], 'Unsafe artifact structure'
    items=load_js(repo/'site/catalog-data.js');byrow={x['row']:x for x in items}
    runs=load(repo/'.publish-local/refresh-20260903/run-inventory.json')
    byroot={Path(r['root']).name:r for r in runs if Path(r['root']).parent==batch}
    groups={}; copied=0; total=0
    for a in data['artifacts']:
        source=source_dir/Path(a['path']).name
        assert source.is_file() and not source.is_symlink()
        body=source.read_bytes()
        assert hashlib.sha256(body).hexdigest()==a['sha256'], 'Artifact digest mismatch'
        row=int(a['row']);n=int(a['case_id'][-1]);item=byrow[row]
        assert item['name']==a['skill_name'], 'Artifact Skill identity mismatch'
        run=byroot.get(a['run']); assert run and run['row']==row and run['case']==n
        public=clean(body,source.name)
        digest=hashlib.sha256(public).hexdigest()[:16]
        target=repo/'site/assets/run-archive'/f'{digest}-{source.name}'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(public);copied+=1;total+=len(public)
        u='assets/run-archive/'+quote(target.name)
        entry=groups.setdefault((row,n,a['run']),{'finishedAt':run['finished'],'status':run['status'],
          'label':'历史执行产物（可能早于当前回答，不用于替代新一轮结果）','prompt':run['prompt'],
          'url':run['url'],'files':[],'images':[]})
        title=a.get('name') or source.name
        entry['files'].append({'url':u,'title':title,'suffix':source.suffix.lstrip('.').upper() or 'FILE'})
        if a['content_type'].startswith('image/') and source.suffix.lower() not in {'.svg'}:entry['images'].append(u)
    for item in items:
        for c in item['cases']:c.pop('archivedDeliverables',None)
    for (row,n,_),entry in groups.items():
        c=byrow[row]['cases'][n-1]
        c.setdefault('archivedDeliverables',[]).append(entry)
    (repo/'site/catalog-data.js').write_bytes(clean(('window.SKILL_ITEMS='+json.dumps(clean_tree(items),ensure_ascii=False,separators=(',',':'))+';\n').encode(),'catalog-data.js'))
    summary=load(repo/'site/sync-summary.json')
    summary['localArtifacts']={'files':copied,'cases':len(groups),'bytes':total,'sourceManifestHash':hashlib.sha256(manifest.read_bytes()).hexdigest(),
      'note':'本地已有附件按归档执行单独展示；未将旧版本产物冒充最新结果。'}
    (repo/'site/sync-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary['localArtifacts'],ensure_ascii=False))

if __name__=='__main__':main()
