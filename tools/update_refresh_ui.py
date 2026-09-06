"""Mechanical template migration; leaves crawling dates separate from refresh dates."""
import json
from pathlib import Path
import re

repo=Path(__file__).resolve().parents[1]
p=repo/'site/index.html'
s=p.read_text()
s=s.replace('看板更新 2026-08-28','看板更新 2026-09-03').replace('看板更新于 2026-08-28','看板更新于 2026-09-03')
s=re.sub(r'(catalog-data\.js\?v=)\d+',r'\g<1>20260903',s)
s=s.replace('收录至少有 1 个豆包 Case 链接的 Skill；点击条目查看 Prompt、豆包与 WorkBuddy 回答及产物','收录全部 1,434 个 Skill；同步至 8 月 28 日暂停前的现有记录，未启动新测试')
s=s.replace('个已有 Case 的 Skill','个 Skill（含待跑条目）').replace('已有 Case 的 Skill 目录','全部 Skill 与执行记录')
s=s.replace('至少有一个豆包 Case 对话链接；重点方向、优先级、用途与实测结果集中浏览','有结果与待跑条目一并展示；对话链接数不等于执行成功数')
s=s.replace('公开迁移版：数据更新时间沿用原记录。','公开版：2026-09-03 同步表格及上次执行归档；未重跑、未重新评分。')
s=s.replace('豆包 ${x.tested}/3 Case','豆包链接 ${x.tested}/3')
s=s.replace("${c.tested?' ✓':' · 待测'}","${c.tested?' · 有链接':' · 无链接'}")
# Collection batches assigned by the owner, kept separate from the dashboard refresh date.
# Rows 1336-1485 are the latest 150 Skills collected in the 2026-08-31 weekly batch.
crawl_dates={str(n):'2026-08-17' for n in range(2,1336)}
crawl_dates.update({str(n):'2026-08-31' for n in range(1336,1486)})
s=re.sub(r'const CRAWL_DATES=\{[^;]+\};','const CRAWL_DATES='+json.dumps(crawl_dates,separators=(',',':'))+';',s,count=1)
s=s.replace(
    '按 Skill 抓取批次筛选（北京时间）；2026-08-17 为历史批次补录，不代表测试或看板更新时间。',
    '按 Skill 抓取批次筛选（北京时间）；2026-08-31 为本周新增 150 条，2026-08-17 为历史批次补录。',
)
helper='''function caseEvidenceHtml(c){
const attempt=c.lastAttempt;
return `<div class="result"><b>记录状态：</b>${esc(c.evidenceNote)}<br><b>题目版本：</b>${esc(c.promptBasis)}${c.revisionNote?`<br>${esc(c.revisionNote)}`:''}</div>
${c.preparedPrompt?`<details><summary>查看后续改写题目（不代表已重测）</summary><div class="box prompt">${esc(c.preparedPrompt)}</div></details>`:''}
${c.previousResultUrl?`<div class="caseactions"><a href="${safeUrl(c.previousResultUrl)}" target="_blank" rel="noopener">此前对话记录 ↗</a></div>`:''}
${attempt?`<details class="attempt-record"><summary>较新执行记录：${esc(attempt.label)} · ${esc(attempt.finishedAt||'时间未记录')}</summary><p>${esc(attempt.note)}</p><div class="label">该次执行题目</div><div class="box prompt">${esc(attempt.prompt||'题目未归档')}</div><div class="label">已捕获的回复（不等于成功完成）</div><div class="box">${esc(attempt.answer||'未捕获可展示回复')}</div></details>`:''}`;
}
'''
if 'function caseEvidenceHtml' not in s:s=s.replace('function openDetail(row)',helper+'function openDetail(row)',1)
needle='${esc(c.prompt)}</div>${caseVerdictHtml(x.row,i)}'
if needle in s and '${caseEvidenceHtml(c)}' not in s:s=s.replace(needle,'${esc(c.prompt)}</div>${caseEvidenceHtml(c)}${caseVerdictHtml(x.row,i)}',1)
s=s.replace('<div class="label">PROMPT</div><div class="box prompt">${esc(c.prompt)}</div>${caseEvidenceHtml(c)}','${caseEvidenceHtml(c)}<div class="label">PROMPT · ${esc(c.promptBasis)}</div><div class="box prompt">${esc(c.prompt)}</div>',1)
s=s.replace('${esc(c.prompt)}</div>${caseEvidenceHtml(c)}${caseVerdictHtml(x.row,i)}','${esc(c.prompt)}</div>${caseVerdictHtml(x.row,i)}',1)
if 'refresh-contained-gallery' not in s:
    s=s.replace('</head>','<style id="refresh-contained-gallery">.provider-panel .horizontal-scroll figure{flex:0 0 100%;min-width:0;max-width:100%;box-sizing:border-box}.provider-panel .horizontal-scroll img{width:100%;max-width:100%;object-fit:contain}</style></head>',1)
if 'function archivedDeliverablesHtml' not in s:
    extra='''function archivedDeliverablesHtml(c){return (c.archivedDeliverables||[]).map(a=>`<details><summary>历史产物归档 · ${esc(a.finishedAt)} · ${a.files.length} 个文件</summary><p>${esc(a.label)}</p><details><summary>这批产物对应的实际题目</summary><div class="box prompt">${esc(a.prompt)}</div></details>${artifactHtml({kind:'bundle',title:'本地归档产物',images:a.images,files:a.files})}</details>`).join('')}
'''
    s=s.replace('function openDetail(row)',extra+'function openDetail(row)',1)
    s=s.replace("${artifactHtml(c.artifact)||'<div class=\"wb-empty\">暂无独立产物附件</div>'}","${artifactHtml(c.artifact)||'<div class=\"wb-empty\">暂无独立产物附件</div>'}${archivedDeliverablesHtml(c)}",1)
if 'refresh-responsive-header' not in s:
    s=s.replace('</head>','<style id="refresh-responsive-header">.hero{flex-wrap:wrap}.hero>div:first-child{flex:1;min-width:240px}.hero .public-release-notice{flex-basis:100%;margin-top:0!important}@media(max-width:620px){.hero{gap:10px}.head{align-items:start;flex-wrap:wrap}.hero h1{font-size:30px}}</style></head>',1)
if "${x.historicalScore!=null?" not in s:
    s=s.replace('${esc(x.conclusion)}</span></div></div><div class="tabs">','${esc(x.conclusion)}${x.historicalScore!=null?`<br>历史表格分数：${esc(x.historicalScore)} / 10；${esc(x.scoreNote)}`:""}</span></div></div><div class="tabs">',1)
p.write_text(s)
