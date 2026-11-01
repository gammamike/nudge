#!/usr/bin/env python3
"""Validate release identity and archive checksums before preparing downloads."""
import argparse
import hashlib
from pathlib import Path
import re
import tarfile
import tomllib


def member_text(archive, name):
    with tarfile.open(archive) as contents:
        member = contents.getmember(name)
        if not member.isfile() or member.size > 1024 * 1024:
            raise ValueError(f'Invalid metadata member: {name}')
        return contents.extractfile(member).read().decode()


def verify(directory, *, tag=None, commit=None, allow_development=False):
    checksums = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  (nudge-[a-zA-Z0-9._+-]+\.tar\.gz)', line)
        if not match or match[2] in checksums:
            raise ValueError('Invalid or repeated checksum entry')
        checksums[match[2]] = match[1]
    if len(checksums) != 2:
        raise ValueError('Expected one source and one Linux x86_64 archive')
    sources = [name for name in checksums if name.endswith('-source.tar.gz')]
    if len(sources) != 1:
        raise ValueError('Expected a matching source archive')
    version = sources[0][6:-14]
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise ValueError('Expected a release version')
    binary = f'nudge-{version}-linux-x86_64.tar.gz'
    if set(checksums) != {sources[0], binary}:
        raise ValueError('Archive versions or architecture differ')
    for name, expected in checksums.items():
        with (directory / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError(f'Checksum mismatch: {name}')
    source_version = tomllib.loads(member_text(directory / sources[0], f'nudge-{version}-source/Cargo.toml'))['package']['version']
    info = dict(line.split('=', 1) for line in member_text(directory / binary, f'nudge-{version}-linux-x86_64/BUILD-INFO').splitlines())
    if source_version != version or info.get('version') != version or info.get('target') != 'x86_64-unknown-linux-musl':
        raise ValueError('Archive build identity mismatch')
    if not allow_development and info.get('dirty') != 'false':
        raise ValueError('Development artifacts cannot be released')
    if tag is not None and tag != f'v{version}':
        raise ValueError('Git tag must match Cargo.toml and archive version')
    if commit is not None and info.get('commit') != commit:
        raise ValueError('Binary was not built from the tagged commit')
    return version, checksums


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--commit', required=True)
    args = parser.parse_args()
    verify(args.dist, tag=args.tag, commit=args.commit)
    print('Release checksums, version, clean build, and commit verified')
