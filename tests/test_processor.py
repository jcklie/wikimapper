import gzip
import os
import sqlite3

import pytest

from wikimapper import WikiMapper, create_index


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


# Rows as they appear in the dumps, columns according to the current MediaWiki schema
PAGE_ROWS = [
    "(1,0,'Brezn',0,0,0.1,'20240125183010','20240125183006',1,10,'wikitext',NULL)",
    "(2,0,'Brezel',1,0,0.2,'20240125183010','20240125183006',2,10,'wikitext',NULL)",
    "(3,1,'Brezn',0,0,0.3,'20240125183010','20240125183006',3,10,'wikitext',NULL)",
    "(4,0,'D\\'_boarische_Woocha',0,0,0.4,'20240125183010','20240125183006',4,10,'wikitext',NULL)",
    "(5,0,'Weißwurscht_(Bayern)',0,0,0.5,'20240125183010','20240125183006',5,10,'wikitext',NULL)",
    "(7,0,'Brezen',1,0,0.7,'20240125183010','20240125183006',7,10,'wikitext',NULL)",
]
PAGE_PROPS_ROWS = [
    "(1,'page_image_free','Brezel.jpg',NULL)",
    "(1,'wikibase_item','Q160525',NULL)",
    "(3,'wikibase_item','Q999',NULL)",
    "(4,'wikibase_item','Q20616808',NULL)",
    "(5,'displaytitle','(1,\\'wikibase_item\\',\\'Q1\\')',NULL)",
    "(5,'wikibase_item','Q1386052',NULL)",
]
REDIRECT_ROWS = [
    "(2,0,'Brezn','','')",
    "(7,0,'Brezn','','')",
    "(8,4,'Brezn','','')",
]


def _write_dump(path: str, table: str, rows, one_row_per_line: bool):
    header = "-- MySQL dump\n\nCREATE TABLE `{0}` (\n  `id` int(8)\n);\n".format(table)
    insert = "INSERT INTO `{0}` VALUES".format(table)
    if one_row_per_line:
        # Layout used by dumps since 2025: one row per line
        body = insert + "\n" + ",\n".join(rows) + ";\n"
    else:
        # Older layout: all rows on the same line as the INSERT statement, split over two statements
        middle = len(rows) // 2
        body = "".join(
            insert + " " + ",".join(part) + ";\n" for part in [rows[:middle], rows[middle:]] if part
        )
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(header + body + "UNLOCK TABLES;\n")


def _write_dumps(path: str, dumpname: str, one_row_per_line: bool):
    for table, rows in [
        ("page", PAGE_ROWS),
        ("page_props", PAGE_PROPS_ROWS),
        ("redirect", REDIRECT_ROWS),
    ]:
        _write_dump(
            os.path.join(path, "{0}-{1}.sql.gz".format(dumpname, table)),
            table,
            rows,
            one_row_per_line,
        )


@pytest.mark.parametrize(
    "one_row_per_line", [True, False], ids=["one row per line", "many rows per line"]
)
def test_create_index_parses_dump_layouts(tmpdir, one_row_per_line: bool):
    path = tmpdir.strpath
    _write_dumps(path, "testwiki-latest", one_row_per_line)

    path_to_db = create_index("testwiki-latest", path, os.path.join(path, "index.db"))

    with sqlite3.connect(path_to_db) as conn:
        rows = conn.execute("SELECT * FROM mapping ORDER BY wikipedia_id").fetchall()

    assert rows == [
        (1, "Brezn", "Q160525"),
        (2, "Brezel", "Q160525"),  # Redirect gets the id of its target
        (4, "D'_boarische_Woocha", "Q20616808"),  # Escaped quote
        (5, "Weißwurscht_(Bayern)", "Q1386052"),  # Not confused by the row in the displaytitle
        (7, "Brezen", "Q160525"),
    ]

    mapper = WikiMapper(path_to_db)
    assert set(mapper.id_to_titles("Q160525")) == {"Brezn", "Brezel", "Brezen"}


def test_create_index_fails_for_empty_dump(tmpdir):
    path = tmpdir.strpath
    _write_dumps(path, "testwiki-latest", True)
    _write_dump(os.path.join(path, "testwiki-latest-page.sql.gz"), "page", [], True)

    with pytest.raises(ValueError):
        create_index("testwiki-latest", path, os.path.join(path, "index.db"))


def test_create_index_fails_for_missing_dump(tmpdir):
    path = tmpdir.strpath
    _write_dumps(path, "testwiki-latest", True)
    os.remove(os.path.join(path, "testwiki-latest-redirect.sql.gz"))
    path_to_db = os.path.join(path, "index.db")
    with open(path_to_db, "w") as f:
        f.write("existing index")

    with pytest.raises(FileNotFoundError):
        create_index("testwiki-latest", path, path_to_db)

    # An existing index is not deleted if the dump is incomplete
    with open(path_to_db) as f:
        assert f.read() == "existing index"
