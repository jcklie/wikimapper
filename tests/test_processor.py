import os
import sqlite3

from wikimapper import create_index

from tests.fixtures import *


def test_create_index(tmpdir, bavarian_wiki_dump):
    path_to_db = tmpdir.mkdir("processor").join("index_test.db").strpath

    create_index(bavarian_wiki_dump.dumpname, bavarian_wiki_dump.path, path_to_db)

    # Check that the file is there
    assert os.path.isfile(path_to_db)

    # Check that it is really a sqlite3 db
    with sqlite3.connect(path_to_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM mapping LIMIT 1000")
        results = c.fetchall()

    assert len(results) > 0
