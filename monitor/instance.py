"""Lock de processo liberado pelo sistema operacional inclusive apos crash."""

import os
from pathlib import Path


class InstanceLock:
    def __init__(self, database):
        path = Path(database).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(str(path) + ".lock", "a+b")
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt

            if os.fstat(self.file.fileno()).st_size == 0:
                self.file.write(b"0")
                self.file.flush()
            self.file.seek(0)
            try:
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self.file.close()
                raise RuntimeError("Ja existe uma instancia para este banco.") from None
        else:
            import fcntl

            try:
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.file.close()
                raise RuntimeError("Ja existe uma instancia para este banco.") from None

    def close(self):
        self.file.close()
