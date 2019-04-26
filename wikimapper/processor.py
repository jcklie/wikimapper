""" Uses a Wikipedia dump to construct a mapping between Wikidata and Wikipedia.
    Credit: Uses parts of https://github.com/jamesmishra/mysqldump-to-csv
"""

import csv
import gzip
import logging
import os
import sqlite3
import sys

_logger = logging.getLogger(__name__)


def _is_insert(line):
    """
    Returns true if the line begins a SQL insert statement.
    """
    return line.startswith("INSERT INTO")


def _get_values(line):
    """
    Returns the portion of an INSERT statement containing values
    """
    return line[line.find("` VALUES ") + 9 :]


def _values_sanity_check(values):
    """
    Ensures that values from the INSERT statement meet basic checks.
    """
    assert values
    assert values[0] == "("
    # Assertions have not been raised
    return True


def _parse_values(values):
    """
    Given a file handle and the raw values from a MySQL INSERT
    statement, write the equivalent CSV to the file
    """
    latest_row = []

    reader = csv.reader(
        [values], delimiter=",", doublequote=False, escapechar="\\", quotechar="'", strict=True
    )

    for reader_row in reader:
        for column in reader_row:
            # If our current string is empty...
            if len(column) == 0 or column == "NULL":
                latest_row.append(chr(0))
                continue
            # If our string starts with an open paren
            if column[0] == "(":
                # Assume that this column does not begin
                # a new row.
                new_row = False
                # If we've been filling out a row
                if len(latest_row) > 0:
                    # Check if the previous entry ended in
                    # a close paren. If so, the row we've
                    # been filling out has been COMPLETED
                    # as:
                    #    1) the previous entry ended in a )
                    #    2) the current entry starts with a (
                    if latest_row[-1][-1] == ")":
                        # Remove the close paren.
                        latest_row[-1] = latest_row[-1][:-1]
                        new_row = True
                # If we've found a new row, write it out
                # and begin our new one
                if new_row:
                    yield latest_row
                    latest_row = []
                # If we're beginning a new row, eliminate the
                # opening parentheses.
                if len(latest_row) == 0:
                    column = column[1:]
            # Add our column to the row we're working on.
            latest_row.append(column)
        # At the end of an INSERT statement, we'll
        # have the semicolon.
        # Make sure to remove the semicolon and
        # the close paren.
        if latest_row[-1][-2:] == ");":
            latest_row[-1] = latest_row[-1][:-2]
            yield latest_row


def create_index(dumpname: str, path_to_dumps: str, path_to_db: str = None) -> str:
    """ Creates an index mapping Wikipedia page titles to Wikidata IDs and vice versa.
    This requires a previously downloaded dump `dumpname` in `path_to_dumps`.

    Args:
        dumpname(str): Name of the Wikipedia SQL  dump that should be used for creating an index.
        path_to_dumps(str): Folder in which the dump has been downloaded to.
        path_to_db(str): Path where the index will be saved to. Defaults to `index_${dump_name}.db`.

    Returns:
        str: The path to the created database.

    """
    if path_to_db is None:
        path_to_db = "index_{0}.db".format(dumpname)

    _logger.info("Creating index for [%s] in [%s]", dumpname, path_to_db)

    wiki_name, date = dumpname.split("-")

    pages_dump = os.path.join(path_to_dumps, dumpname + "-page.sql.gz")
    page_props_dump = os.path.join(path_to_dumps, dumpname + "-page_props.sql.gz")
    redirects_dump = os.path.join(path_to_dumps, dumpname + "-redirect.sql.gz")

    csv.field_size_limit(sys.maxsize)

    # (Re)Create the database file
    try:
        os.remove(path_to_db)
    except FileNotFoundError:
        pass

    conn = sqlite3.connect(path_to_db, isolation_level="EXCLUSIVE")

    with conn:
        conn.execute(
            """CREATE TABLE mapping (
            wikipedia_id int PRIMARY KEY ,
            wikipedia_title text,
            wikidata_id text)"""
        )

    c = conn.cursor()

    # Parse the Wikipedia page dump; extract page id and page title from the sql
    # https://www.mediawiki.org/wiki/Manual:Page_table
    _logger.info("Parsing pages dump")
    with gzip.open(pages_dump, "rt", encoding="utf-8", newline="\n") as f:
        for line in f:
            # Look for an INSERT statement and parse it.
            if not _is_insert(line):
                continue

            values = _get_values(line)

            for v in _parse_values(values):
                # Filter the namespace; only use real articles
                # https://www.mediawiki.org/wiki/Manual:Namespace
                if v[1] == "0":
                    c.execute(
                        "INSERT INTO mapping (wikipedia_id, wikipedia_title) VALUES (?, ?)",
                        (v[0], v[2]),
                    )

    conn.commit()

    # We create this index here as all titles have been inserted now.
    # Doing it earlier would recreate the index on every title insert.
    _logger.info("Creating database index on 'wikipedia_title'")
    conn.execute("""CREATE UNIQUE INDEX idx_wikipedia_title ON mapping(wikipedia_title);""")
    conn.commit()

    # Parse the Wikipedia page property dump; extract page id and Wikidata id from the sql
    # https://www.mediawiki.org/wiki/Manual:Page_props_table/en
    _logger.info("Parsing page properties dump")
    with gzip.open(page_props_dump, "r") as f:
        for line in f:
            line = line.decode("utf-8", "ignore")

            # Look for an INSERT statement and parse it.
            if not _is_insert(line):
                continue

            values = _get_values(line)
            for v in _parse_values(values):
                # The page property table contains many properties, we only care about the Wikidata id
                if v[1] == "wikibase_item":
                    c.execute(
                        "UPDATE mapping SET wikidata_id = ? WHERE wikipedia_id = ?", (v[2], v[0])
                    )
    conn.commit()

    # Parse the Wikipedia redirect dump; fill in missing Wikidata ids
    # https://www.mediawiki.org/wiki/Manual:Redirect_table
    _logger.info("Parsing redirects dump")
    with gzip.open(redirects_dump, "rt", encoding="utf-8", newline="\n") as f:
        for line in f:
            # Look for an INSERT statement and parse it.
            if not _is_insert(line):
                continue

            values = _get_values(line)

            for v in _parse_values(values):
                source_wikipedia_id = v[0]
                target_title = v[2]
                namespace = v[1]

                # We only care about main articles
                if namespace != "0":
                    continue

                c.execute(
                    "SELECT wikidata_id FROM mapping WHERE wikipedia_title = ?", (target_title,)
                )
                result = c.fetchone()

                if result is None or result[0] is None:
                    continue

                wikidata_id = result[0]
                c.execute(
                    "UPDATE mapping SET wikidata_id = ? WHERE wikipedia_id = ?",
                    (wikidata_id, source_wikipedia_id),
                )

    conn.commit()

    _logger.info("Creating database index on 'wikidata_id'")
    conn.execute("""CREATE INDEX idx_wikidata_id ON mapping(wikidata_id);""")
    conn.commit()

    c.close()
    conn.close()

    return path_to_db
