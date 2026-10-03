"""Read-only exact Ubuntu HWE headers/config/symbol-table gate."""
import hashlib
from pathlib import Path
import sys

NOBLE = {
    '.config': '354a25b259e8245db07f99c132a3f8325ac887d00a6fca9360105defbe2ca2b3',
    'Module.symvers': '5135c3512b8d20245a85201d3e44746d6fd5fcff598a312fbe4bac7ce74a602a',
}

RESOLUTE = {
    '.config': 'e75c0adab6020e72844d7431cf801a02b94ed32efc251c3b0fb80c021d065180',
    'Module.symvers': 'c5c5bedb68bcd9ccda29884fbfc955a60153a16fc70eec5632e1a8373a1fbc65',
}
PROFILES = {'noble': (NOBLE, 'x86_64-linux-gnu-gcc-13'),
            'resolute': (RESOLUTE, 'x86_64-linux-gnu-gcc-15')}

def validate(root):
    root = Path(root)
    release = (root / 'include/generated/utsrelease.h').read_text()
    if '#define UTS_RELEASE "7.0.0-34-generic"' not in release:
        raise ValueError('Expected Ubuntu ABI 7.0.0-34-generic')
    actual = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
              for name in ('.config', 'Module.symvers')}
    for profile, (expected, compiler) in PROFILES.items():
        if actual == expected:
            return profile, compiler
    raise ValueError('Config/Module.symvers do not match either validated Ubuntu 24.04 HWE or 26.04 amd64 target; review required')

if __name__ == '__main__':
    try:
        profile, compiler = validate(sys.argv[1])
    except (OSError, ValueError, IndexError) as exc:
        print(f'Build target rejected: {exc}', file=sys.stderr)
        sys.exit(2)
    print(compiler)
    print(f'Verified exact Ubuntu {profile} amd64 ABI, config and Module.symvers', file=sys.stderr)
