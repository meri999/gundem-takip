import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY,
    source TEXT, category TEXT, title TEXT, summary TEXT,
    link TEXT UNIQUE, published TEXT, fetched TEXT, topics TEXT
);
CREATE INDEX IF NOT EXISTS ix_items_pub ON items(published);
CREATE TABLE IF NOT EXISTS trends(
    date TEXT, source TEXT, rank INTEGER, term TEXT, value REAL,
    UNIQUE(date, source, term)
);
CREATE TABLE IF NOT EXISTS thinktank(
    kurum TEXT, baslik TEXT, ozet TEXT, link TEXT UNIQUE, tarih TEXT, konular TEXT, alindi TEXT
);
CREATE TABLE IF NOT EXISTS kurulus(
    kurum TEXT, baslik TEXT, ozet TEXT, link TEXT UNIQUE, tarih TEXT, konular TEXT, alindi TEXT
);
CREATE TABLE IF NOT EXISTS events(
    date TEXT, kind TEXT, source TEXT, title TEXT, detail TEXT, link TEXT, topics TEXT,
    UNIQUE(date, kind, source, title)
);
"""


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()
