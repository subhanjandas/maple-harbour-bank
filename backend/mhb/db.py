from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

class Database:
    def __init__(self, url):
        self.pool = ConnectionPool(url, min_size=1, max_size=12, timeout=5,
                                   kwargs={'row_factory': dict_row}, open=False)

    @contextmanager
    def transaction(self, tenant=None):
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("SET LOCAL lock_timeout='3s'")
                conn.execute("SET LOCAL statement_timeout='15s'")
                if tenant is not None:
                    conn.execute("SELECT set_config('mhb.tenant',%s,true)", (tenant,))
                yield conn
