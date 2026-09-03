"""Create a new public-only copy of the existing static dashboard.

Usage: python3 tools/prepare_public.py /path/to/integrated-dist
Never modifies the source and refuses to overwrite an existing public copy.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from audit_public import audit, PATTERNS, PLACEHOLDER, DENIED

REPO = Path(__file__).resolve().parents[1]
ALLOWED = {'index.html', 'catalog-data.js', 'workbuddy-card-data.js', 'provider-evaluation-data.js', 'assets'}
changes = []


def clean(data, label):
    if zipfile.is_zipfile(io.BytesIO(data)):
        out = io.BytesIO()
        removed = []
        with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                if info.is_dir():
                    continue
                if DENIED.search(info.filename):
                    removed.append(info.filename)
                    changes.append({'path': label + '::' + info.filename, 'action': 'excluded_environment_file'})
                    continue
                dst.writestr(info, clean(src.read(info), label + '::' + info.filename))
            if removed:
                dst.writestr('PUBLIC_RELEASE_NOTICE.txt', 'Public copy: environment files omitted; credentials must be supplied locally.\n' + '\n'.join(removed))
        return out.getvalue()
    try:
        s = data.decode('utf8')
    except UnicodeDecodeError:
        return data
    original = s
    s = re.sub(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----', '[REDACTED_PRIVATE_KEY_FOR_PUBLIC_RELEASE]', s)
    for rule, regex in PATTERNS.items():
        def replace(m):
            if PLACEHOLDER.search(m.group()):
                return m.group()
            if m.lastindex:
                start, end = m.span(1)
                return m.group()[:start-m.start()] + 'REDACTED_FOR_PUBLIC_RELEASE' + m.group()[end-m.start():]
            return 'REDACTED_FOR_PUBLIC_RELEASE'
        s = regex.sub(replace, s)
    if label == 'index.html':
        s = s.replace('内部 Skill 评测目录', 'Skill 评测目录')
        # Keep the original data-update date: migration is not a data refresh.
        marker = '</header>'
        notice = '<p class="public-release-notice" style="font-size:14px;margin:12px 0;color:#64748b">公开迁移版：数据更新时间沿用原记录。部分原始会话或附件链接可能需要原平台权限；示例凭证已脱敏，部分压缩附件中的环境配置文件已移除。</p>'
        s = s.replace(marker, notice + marker, 1)
    if s != original:
        changes.append({'path': label, 'action': 'public_copy_sanitized_or_labeled'})
    return s.encode('utf8')


def main():
    src = Path(sys.argv[1]).resolve()
    dest = REPO / 'site'
    if dest.exists():
        raise SystemExit('site already exists; refusing to overwrite local edits')
    if not (src / 'index.html').is_file():
        raise SystemExit('Missing index.html')
    initial = audit(src)
    unsafe = [x for x in initial['findings'] if x['rule'] in {'symlink', 'archive_depth_limit', 'archive_size_limit', 'encrypted_archive', 'github_file_size'}]
    if unsafe:
        raise SystemExit('Unsafe source structure; inspect audit before packaging')
    for f in sorted(src.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if rel.parts[0] not in ALLOWED:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(clean(f.read_bytes(), str(rel)))
    (dest / '.nojekyll').touch()
    result = audit(dest)
    (REPO / 'public-audit.json').write_text(json.dumps({'audit': result, 'changes': changes}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'passed': result['passed'], 'files': result['files'], 'bytes': result['bytes'], 'changed_items': len(changes)}, ensure_ascii=False))
    if not result['passed']:
        raise SystemExit('Public audit failed; do not publish')


if __name__ == '__main__':
    main()
