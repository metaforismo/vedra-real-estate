#!/usr/bin/env python3
"""Create a source ZIP with a SHA256 manifest, never runtime data or credentials."""
from pathlib import Path
import argparse
import hashlib
import zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','venv','__pycache__','.pytest_cache','node_modules','data','backups','dist','artifacts','build','.idea','.vscode'}


def include(path):
    relative=path.relative_to(ROOT)
    if any(part in EXCLUDED or part.endswith('.egg-info') for part in relative.parts):return False
    name=path.name
    if name.startswith('.env') and name!='.env.example':return False
    if name.endswith(('.env','.pyc','.log','.sqlite3','.db','.ttf','.otf','.woff','.woff2')):return False
    if name in ('.DS_Store','MANIFEST.sha256','.coverage'):return False
    return path.is_file() and not path.is_symlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/Vedra_0.2.0_Complete.zip')
    args=parser.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    paths=sorted(p for p in ROOT.rglob('*') if include(p) and p.resolve()!=args.output.resolve())
    manifest=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in paths)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in paths:archive.write(p,'vedra-real-estate/'+p.relative_to(ROOT).as_posix())
        archive.writestr('vedra-real-estate/MANIFEST.sha256',manifest)
    print(f'{len(paths)+1} files → {args.output} ({args.output.stat().st_size:,} bytes)')
    print('SHA256 '+hashlib.sha256(args.output.read_bytes()).hexdigest())

if __name__=='__main__':main()
