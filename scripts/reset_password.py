#!/usr/bin/env python3
"""Local administrative recovery; requires access to the private data directory."""
from pathlib import Path
import argparse
import getpass
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('email')
    args=parser.parse_args()
    from app.config import load_env,Settings
    from app.db import Database
    from app.security import password_hash
    load_env();settings=Settings()
    if not settings.db_path.exists():parser.error('Database non trovato. Avvia prima l’app.')
    db=Database(settings.db_path)
    user=db.one('SELECT id FROM users WHERE email=?',(args.email.strip().lower(),))
    if not user:parser.error('Utente non trovato.')
    password=getpass.getpass('Nuova password (almeno 12 caratteri): ')
    if len(password)<12 or len(password)>256:parser.error('Lunghezza password non valida.')
    if password!=getpass.getpass('Ripeti la password: '):parser.error('Le password non coincidono.')
    with db.transaction() as con:
        con.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(password),user['id']))
        con.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
    print('Password aggiornata. Tutte le sessioni di questo utente sono state revocate.')

if __name__=='__main__':main()
