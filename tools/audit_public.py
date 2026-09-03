"""Offline preflight. Reports rule names and paths, NEVER matching secrets.

Heuristic scan, not proof that all confidential/personal content is absent.
Archive contents are read, never executed or extracted to disk.
"""
import collections
import io
import json
import re
import sys
import zipfile
from pathlib import Path

RULES = {
    'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
    'github_token': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
    'cloud_key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'api_key': r'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b',
    'jwt': r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',
    'credential_query': r'[?&](?:ak|api_key|access_token|auth_token|client_secret|password)=[A-Za-z0-9_+/%.-]{12,}',
    'assigned_secret': r'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|app[_-]?secret|password|passwd)\s*["']?\s*[:=]\s*["']([A-Za-z0-9_+/.=-]{16,})["']''',
    'bearer': r'(?i)\bBearer\s+[A-Za-z0-9_+/.=-]{24,}',
}
PATTERNS = {k: re.compile(v) for k, v in RULES.items()}
DENIED = re.compile(r'(?i)(?:^|/)(?:\.git|\.env(?:\..*)?|pkcs11\.txt|cookies?\.(?:json|txt)|.*auth.*cache|.*login.*cache)(?:/|$)')
PLACEHOLDER = re.compile(r'(?i)(?:example|placeholder|your[_-]|redacted|dummy|xxxxxxxx|test[_-])')


def audit(root):
    root = Path(root).resolve()
    findings, extensions, hosts = [], collections.Counter(), collections.Counter()
    total = 0

    def scan_bytes(data, label, depth=0):
        if zipfile.is_zipfile(io.BytesIO(data)):
            if depth > 3:
                findings.append({'path': label, 'rule': 'archive_depth_limit'})
                return
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(x.file_size for x in z.infolist()) > 200_000_000:
                    findings.append({'path': label, 'rule': 'archive_size_limit'})
                    return
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    if info.flag_bits & 1:
                        findings.append({'path': label, 'rule': 'encrypted_archive'})
                        continue
                    scan_bytes(z.read(info), label + '::' + info.filename, depth + 1)
            return
        s = data.decode('utf-8', errors='replace')
        if DENIED.search(label):
            findings.append({'path': label, 'rule': 'forbidden_path'})
        for name, regex in PATTERNS.items():
            matches = [m for m in regex.finditer(s) if not PLACEHOLDER.search(m.group())]
            if matches:
                findings.append({'path': label, 'rule': name, 'count': len(matches)})
        for host in re.findall(r'https?://([A-Za-z0-9.-]+)', s):
            if any(x in host for x in ('feishu', 'larkoffice', 'doubao', 'bytedance', 'aiforce')):
                hosts[host] += 1

    files = sorted(root.rglob('*'))
    for f in files:
        if f.is_symlink():
            findings.append({'path': str(f.relative_to(root)), 'rule': 'symlink'})
            continue
        if not f.is_file():
            continue
        size = f.stat().st_size
        total += size
        extensions[f.suffix or '(none)'] += 1
        if size >= 100_000_000:
            findings.append({'path': str(f.relative_to(root)), 'rule': 'github_file_size'})
        scan_bytes(f.read_bytes(), str(f.relative_to(root)))
    return {'passed': not findings, 'files': sum(extensions.values()), 'bytes': total,
            'findings': findings, 'external_service_hosts': dict(hosts),
            'note': 'Pattern-based scan only; external link access and image/PDF content need separate review.'}


if __name__ == '__main__':
    result = audit(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['passed'] else 1)
