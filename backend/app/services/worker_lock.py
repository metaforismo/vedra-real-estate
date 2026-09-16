"""An OS lock prevents two schedulers sharing the same SQLite workspace."""
import os


class WorkerLock:
    def __init__(self,path):
        self.path=path
        self.file=None

    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.file=open(self.path,'a+b')
        try:
            if os.name=='nt':
                import msvcrt
                self.file.seek(0)
                self.file.write(b'0'); self.file.flush(); self.file.seek(0)
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close();self.file=None
            raise RuntimeError('Un altro processo Vedra usa questo workspace. Avvia un solo worker.') from exc

    def release(self):
        if self.file:
            if os.name=='nt':
                import msvcrt
                self.file.seek(0);msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            self.file.close();self.file=None

    def assert_owned(self):
        if not self.file:
            raise RuntimeError('Worker lock non acquisito.')


class PostgresWorkerLock:
    """A session lock fences the single collector across hosts and API processes."""
    def __init__(self, db):
        import hashlib
        self.db = db
        self.key = int.from_bytes(hashlib.sha256(('vedra:worker:' + db.driver.schema).encode()).digest()[:8], 'big', signed=True)
        self.connection = None

    def acquire(self):
        con = self.db.connect()
        try:
            row = con.execute('SELECT pg_try_advisory_lock(?) AS acquired', (self.key,)).fetchone()
            con.commit()
            if not row['acquired']:
                raise RuntimeError('Un altro worker usa già questo schema Vedra.')
        except BaseException:
            con.rollback()
            con.close()
            raise
        self.connection = con

    def assert_owned(self):
        if not self.connection:
            raise RuntimeError('Worker lock non acquisito.')
        self.connection.execute('SELECT 1')
        self.connection.commit()

    def release(self):
        if self.connection:
            try:
                self.connection.execute('SELECT pg_advisory_unlock(?)', (self.key,))
                self.connection.commit()
            finally:
                self.connection.close()
                self.connection = None
