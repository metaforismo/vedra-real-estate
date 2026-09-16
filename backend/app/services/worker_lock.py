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
