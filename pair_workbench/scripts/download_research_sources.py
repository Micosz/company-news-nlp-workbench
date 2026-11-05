#!/usr/bin/env python3
"""Download pinned public source archives; verify hashes; never run source code."""
import argparse
import hashlib
import urllib.request
from pathlib import Path

SOURCES = {
    'eventstoryline-46edefee.zip': (
        'https://github.com/tommasoc80/EventStoryLine/archive/46edefee5e82e0917b823abe0a18bf8c7770f15c.zip',
        'bb3574fc793fceb79e281ca182adf7a52890b5869ccbf4f2f28512d4272eff58'),
    'cdec-wn-dataset-v1.tar.gz': (
        'https://github.com/adithya7/cdec-wikinews/releases/download/v1.0/cdec-wn-dataset.tar.gz',
        '7d5b1790145fc0603913aa24b60ce1bd8104196191289363fb6e2eb73c8d346d'),
}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def download(destination):
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    for name,(url,expected) in SOURCES.items():
        target=destination/name
        if target.exists():
            if sha(target)!=expected: raise ValueError(f'ไฟล์ที่มีอยู่ SHA-256 ไม่ตรง: {target}')
            print('Verified',target);continue
        partial=target.with_suffix(target.suffix+'.part')
        print('Downloading',name,flush=True)
        with urllib.request.urlopen(url,timeout=120) as response, partial.open('xb') as out:
            for block in iter(lambda:response.read(1024*1024),b''):out.write(block)
        if sha(partial)!=expected: raise ValueError(f'Source SHA-256 changed; inspect {partial}')
        partial.replace(target)
        print('Verified',target)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,default=Path('local_data/external_sources'));a=p.parse_args()
    try:download(a.destination)
    except (OSError,ValueError) as exc:p.exit(2,f'ดาวน์โหลดไม่สำเร็จ: {exc}\n')
