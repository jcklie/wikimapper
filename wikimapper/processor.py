r""" Uses a Wikipedia dump to construct a mapping between Wikidata and Wikipedia.
    Credit: Originally used parts of https://github.com/jamesmishra/mysqldump-to-csv

Goal
----
Build an SQLite database (the "index") with a single table::

    mapping(wikipedia_id int PRIMARY KEY, wikipedia_title text, wikidata_id text)

It holds one row for every page in the main namespace of one Wikipedia (articles and redirects).
Example with real pages of the Bavarian Wikipedia (barwiki)::

    wikipedia_id | wikipedia_title | wikidata_id
    -------------+-----------------+------------
            1997 | Brezn           | Q160525        the article about pretzels
           24100 | Brezel          | Q160525        a redirect to Brezn, it gets the id of Brezn

`WikiMapper` (mapper.py) answers all its questions with lookups in this table, e.g.
`title_to_id("Brezel")` returns "Q160525" and `id_to_titles("Q160525")` returns all titles of
the item, including its redirects. Two database indexes make these lookups fast: one on
`wikipedia_title` (unique) and one on `wikidata_id`.

Input
-----
Three dumps from https://dumps.wikimedia.org/<wiki>/<date>/ (see download.py)::

    dump                             contains                          used for
    <wiki>-<date>-page.sql.gz        every page: id, namespace, title  wikipedia_id, wikipedia_title
    <wiki>-<date>-page_props.sql.gz  properties, e.g. the Wikidata id  wikidata_id
    <wiki>-<date>-redirect.sql.gz    the target of each redirect       wikidata_id of redirects

Each one is a gzip-compressed MySQL dump: a `CREATE TABLE` statement, followed by `INSERT`
statements that hold the rows. Real rows from barwiki, shortened (`...`)::

    page:        (1997,0,'Brezn',0,0,0.745707325237,'20260130182758',...,'wikitext',NULL)
                 (5740,1,'Brezn',0,0,0.533009202776,...)     the talk page of Brezn (namespace 1)
                 (24100,0,'Brezel',1,1,0.993641585491,...)   page_is_redirect = 1
    page_props:  (1997,'page_image_free','Pretzel_01-14.jpg',NULL)
                 (1997,'wikibase_item','Q160525',NULL)      the Wikidata id of page 1997
    redirect:    (24100,0,'Brezn','','')                    page 24100 redirects to Brezn

Strings are enclosed in `'`, and special characters inside them are escaped with a backslash:
the title D'_boarische_Woocha is written as 'D\'_boarische_Woocha'.

The rows of an `INSERT` statement come in one of two layouts, and both are supported::

    older dumps:       INSERT INTO `page` VALUES (1,0,'Main_Page',...),(2,2,'Purodha',...),...;
    dumps since 2025:  INSERT INTO `page` VALUES
                       (1,0,'Main_Page',...),
                       (2,2,'Purodha',...),
                       ...;

Steps
-----
1. `page`: insert id and title of every page in namespace 0 (articles and redirects). The other
   namespaces hold talk pages, user pages, templates, ..., which have no place in the mapping.
2. `page_props`: set `wikidata_id` of every page that has a `wikibase_item` property.
3. `redirect`: redirects usually have no Wikidata id of their own, so they get the one of the page
   they point to (Brezel gets Q160525 from Brezn).
4. Create the index on `wikidata_id`.

For the English Wikipedia of October 2026 this results in 19,315,587 rows, 7,590,958 of them get
their Wikidata id in step 2 and most of the others in step 3 (19,280,223 rows have one in the end).
"""

import gzip
import logging
import os
import re
import sqlite3
from typing import Iterator, Optional, Tuple

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------------------------
# Row patterns
#
# The dumps are not parsed as SQL. Instead, regular expressions find the rows that are needed and
# extract only the leading columns that are needed. `re.findall` returns one tuple of the captured
# groups `( ... )` per row, scanning the line from left to right. This works the same way no matter
# whether a line holds one row (new layout) or thousands of rows (old layout).
#
# A match can never start inside of a string: inside a string, every quote is escaped (`\'`), but
# all patterns below need an unescaped quote right after the leading numbers. For example, the
# property value "(1,'wikibase_item','Q1')" is stored as '(1,\'wikibase_item\',\'Q1\')', which
# does not match `_PAGE_PROPS_ROW`.
#
# The patterns only match the rows that are needed (namespace 0, Wikidata ids), so the regex
# engine skips all other rows without handing them to Python, and they match strings in long runs
# (see `_STRING`). Both together reduce the time for parsing the English dumps from 193 s (matching
# every row and filtering in Python) to 55 s.
# ------------------------------------------------------------------------------------------------

# A quoted MySQL string, e.g. 'D\'_boarische_Woocha'; the group captures the content without the
# enclosing quotes, still escaped (`_unescape` removes the backslashes):
#
#   '                 the opening quote
#   (                 start of the captured content
#     [^'\\]*           a run of characters that are neither a quote nor a backslash
#     (?:\\.[^'\\]*)*   any number of: an escape (a backslash and the character after it, e.g. \')
#                       followed by the next run
#   )                 end of the captured content
#   '                 the closing quote: the first quote that is not escaped
#
# Matching whole runs at a time is much faster than deciding for every single character, as the
# equivalent `'((?:[^'\\]|\\.)*)'` would.
_STRING = r"'([^'\\]*(?:\\.[^'\\]*)*)'"

# A row of the page table: (page_id, page_namespace, page_title, ...)
# https://www.mediawiki.org/wiki/Manual:Page_table
#
#   \(        the opening parenthesis of the row
#   (\d+)     page_id, captured
#   ,0,       page_namespace must be exactly 0, the main namespace (articles and their redirects),
#             see https://www.mediawiki.org/wiki/Manual:Namespace. Rows of other namespaces, e.g.
#             (5740,1,'Brezn',...), do not match and are skipped by the regex engine itself.
#   _STRING   page_title, captured. The remaining columns of the row are not needed.
#
# (1997,0,'Brezn',0,0,0.745707325237,...)  ->  ("1997", "Brezn")
_PAGE_ROW = re.compile(r"\((\d+),0," + _STRING)

# A row of the page properties table: (pp_page, pp_propname, pp_value, pp_sortkey)
# https://www.mediawiki.org/wiki/Manual:Page_props_table
#
#   \(                  the opening parenthesis of the row
#   (\d+)               pp_page, the page id, captured
#   ,'wikibase_item',   pp_propname must be exactly wikibase_item, the property that holds the
#                       Wikidata id. Other properties (page images, display titles, ...) do not
#                       match. They make up most of the table.
#   _STRING             pp_value, the Wikidata id, captured
#
# (1997,'wikibase_item','Q160525',NULL)  ->  ("1997", "Q160525")
_PAGE_PROPS_ROW = re.compile(r"\((\d+),'wikibase_item'," + _STRING)

# A row of the redirect table: (rd_from, rd_namespace, rd_title, rd_interwiki, rd_fragment)
# https://www.mediawiki.org/wiki/Manual:Redirect_table
#
#   \(        the opening parenthesis of the row
#   (\d+)     rd_from, the page id of the redirect itself, captured
#   ,0,       rd_namespace, the namespace of the TARGET, must be 0: only redirects to articles
#   _STRING   rd_title, the title of the target page, captured
#
# Note that rd_namespace is the namespace of the target, not of the redirect. Redirects that are
# not in namespace 0 themselves are not in the mapping table, so updating them changes nothing.
#
# (24100,0,'Brezn','','')  ->  ("24100", "Brezn")
_REDIRECT_ROW = re.compile(r"\((\d+),0," + _STRING)

# A backslash and the character it escapes, e.g. \' or \\
_ESCAPE = re.compile(r"\\(.)")


def _unescape(value: str) -> str:
    """Removes the MySQL escapes from a string captured by `_STRING`.

    Every backslash is dropped and the character after it is kept: `D\\'_boarische_Woocha` becomes
    `D'_boarische_Woocha` and `C:\\\\` becomes `C:\\`. Titles and Wikidata ids almost never contain
    an escape, so the (slower) substitution only runs if there is a backslash at all.
    """
    return _ESCAPE.sub(r"\1", value) if "\\" in value else value


def _data_lines(path: str, errors: str) -> Iterator[str]:
    """Yields the lines of `path` that contain rows of an INSERT statement.

    Older dumps put all rows of an INSERT statement on the same line as `INSERT INTO ... VALUES`,
    newer ones (2025 onwards) put every row on its own line. Both layouts are supported.

    The dump is decompressed and read line by line, so even the dumps of the English Wikipedia
    (several GB uncompressed) never have to fit into memory at once.

    Args:
        path (str): Path to a `.sql.gz` dump.
        errors (str): How invalid UTF-8 is handled, see `_parse_pages` and `_parse_wikidata_ids`.

    """
    # "rt": decompress and decode to text. newline="\n": a line ends only at "\n", exactly as the
    # dump writes it, without any translation of line endings.
    with gzip.open(path, "rt", encoding="utf-8", errors=errors, newline="\n") as f:
        for line in f:
            # Rows are either on the `INSERT INTO ... VALUES ...` line itself (old layout) or on
            # the lines after it, each starting with "(" (new layout). All other lines, like
            # comments and the `CREATE TABLE` statement, are skipped.
            if line.startswith("(") or line.startswith("INSERT INTO"):
                yield line


def _parse_pages(path: str) -> Iterator[Tuple[int, str]]:
    """Yields `(wikipedia_id, wikipedia_title)` of every page in namespace 0 of the page dump.

    The order of the values matches the parameters of the `INSERT` in `create_index`.
    Example: (1997,0,'Brezn',...) -> (1997, "Brezn")
    """
    # Titles are always valid UTF-8 in the page dump (all 66 million rows of the English dump of
    # October 2026 are), so an invalid byte means the file is damaged: fail instead of silently
    # creating wrong titles.
    for line in _data_lines(path, errors="strict"):
        for page_id, title in _PAGE_ROW.findall(line):
            yield int(page_id), _unescape(title)


def _parse_wikidata_ids(path: str) -> Iterator[Tuple[str, int]]:
    """Yields `(wikidata_id, wikipedia_id)` of every `wikibase_item` row of the page props dump.

    The order of the values matches the parameters of the `UPDATE` in `create_index`.
    Example: (1997,'wikibase_item','Q160525',NULL) -> ("Q160525", 1997)
    """
    # The page properties contain binary values that are not valid UTF-8 (e.g. compressed
    # template data, 74,333 lines in the English dump of October 2026). Invalid bytes are dropped,
    # which does not affect the Wikidata ids: they are plain ASCII like Q160525.
    for line in _data_lines(path, errors="ignore"):
        for page_id, value in _PAGE_PROPS_ROW.findall(line):
            yield _unescape(value), int(page_id)


def _parse_redirects(path: str) -> Iterator[Tuple[str, int]]:
    """Yields `(target_title, redirect_id)` of every redirect to namespace 0 of the redirect dump.

    The order of the values matches the parameters of the redirect `UPDATE` in `create_index`.
    Example: (24100,0,'Brezn','','') -> ("Brezn", 24100)
    """
    # Invalid UTF-8 is ignored here as well, as it has been done since
    # https://github.com/jcklie/wikimapper/issues/12
    for line in _data_lines(path, errors="ignore"):
        for source_id, target_title in _REDIRECT_ROW.findall(line):
            yield _unescape(target_title), int(source_id)


def create_index(dumpname: str, path_to_dumps: str, path_to_db: Optional[str] = None) -> str:
    """Creates an index mapping Wikipedia page titles to Wikidata IDs and vice versa.
    This requires a previously downloaded dump `dumpname` in `path_to_dumps`.

    The index is the SQLite table `mapping(wikipedia_id, wikipedia_title, wikidata_id)` described
    at the top of this module. It is built in four steps: pages, Wikidata ids, redirects, indexes.
    An existing index at `path_to_db` is replaced.

    Args:
        dumpname(str): Name of the Wikipedia SQL  dump that should be used for creating an index.
        path_to_dumps(str): Folder in which the dump has been downloaded to.
        path_to_db(str): Path where the index will be saved to. Defaults to `index_${dump_name}.db`.

    Returns:
        str: The path to the created database.

    Raises:
        FileNotFoundError: If one of the three dumps is missing. The existing index is kept.
        ValueError: If not a single page could be parsed, e.g. because the dump format changed.

    """
    if path_to_db is None:
        path_to_db = "index_{0}.db".format(dumpname)

    _logger.info("Creating index for [%s] in [%s]", dumpname, path_to_db)

    # The three dumps as named by download.py, e.g. data/barwiki-latest-page.sql.gz
    pages_dump = os.path.join(path_to_dumps, dumpname + "-page.sql.gz")
    page_props_dump = os.path.join(path_to_dumps, dumpname + "-page_props.sql.gz")
    redirects_dump = os.path.join(path_to_dumps, dumpname + "-redirect.sql.gz")

    # Check all dumps before touching the existing index. Otherwise a missing redirect dump would
    # only be noticed after the old index has been deleted and half of the new one has been built,
    # which leaves an index without redirects behind.
    for dump in [pages_dump, page_props_dump, redirects_dump]:
        if not os.path.isfile(dump):
            raise FileNotFoundError("Dump [{0}] does not exist".format(dump))

    # (Re)Create the database file
    try:
        os.remove(path_to_db)
    except FileNotFoundError:
        pass

    # With an isolation level, sqlite3 starts a transaction before the first change and every
    # `with conn:` block below commits its changes at the end (or rolls them back on an error).
    # Writing millions of rows in one transaction is far faster than committing every single row.
    # EXCLUSIVE locks the database for other connections while it is written.
    conn = sqlite3.connect(path_to_db, isolation_level="EXCLUSIVE")

    # wikipedia_id is the PRIMARY KEY: page ids are unique, and the updates below look rows up by
    # it. wikidata_id stays NULL until a Wikidata id is known for the page.
    with conn:
        conn.execute(
            """CREATE TABLE mapping (
            wikipedia_id int PRIMARY KEY ,
            wikipedia_title text,
            wikidata_id text)"""
        )

    # Step 1: Parse the Wikipedia page dump; extract page id and page title from the sql.
    # `executemany` takes the rows directly from the generator, one after another, so the parsed
    # rows are never all in memory. `rowcount` is the number of inserted rows.
    _logger.info("Parsing pages dump")
    with conn:
        count = conn.executemany(
            "INSERT INTO mapping (wikipedia_id, wikipedia_title) VALUES (?, ?)",
            _parse_pages(pages_dump),
        ).rowcount
    _logger.info("Inserted [%d] pages", count)

    # Every Wikipedia has pages, so no rows at all means that the rows were not recognized, e.g.
    # because the dump format changed. Fail loudly instead of writing an empty index.
    if count == 0:
        conn.close()
        raise ValueError(
            "No pages could be parsed from [{0}], the dump format may have changed".format(
                pages_dump
            )
        )

    # We create this index here as all titles have been inserted now.
    # Doing it earlier would recreate the index on every title insert.
    # The redirect step below looks up every redirect target by its title, which needs this index,
    # and it is used by `WikiMapper.title_to_id`. UNIQUE: a title exists only once per namespace.
    _logger.info("Creating database index on 'wikipedia_title'")
    with conn:
        conn.execute("""CREATE UNIQUE INDEX idx_wikipedia_title ON mapping(wikipedia_title);""")

    # Step 2: Parse the Wikipedia page property dump; extract page id and Wikidata id from the sql.
    # The page props of other namespaces (categories, templates, ...) match no row of the mapping
    # table, so they change nothing; `rowcount` only counts the rows that were actually updated.
    _logger.info("Parsing page properties dump")
    with conn:
        count = conn.executemany(
            "UPDATE mapping SET wikidata_id = ? WHERE wikipedia_id = ?",
            _parse_wikidata_ids(page_props_dump),
        ).rowcount
    _logger.info("Mapped [%d] pages to Wikidata", count)

    # Step 3: Parse the Wikipedia redirect dump; give redirects the Wikidata id of their target.
    # For every redirect (target_title, redirect_id), e.g. ("Brezn", 24100):
    # - the subquery looks up the Wikidata id of the target page by its title (via the title
    #   index), e.g. Q160525 for Brezn;
    # - COALESCE takes that id, or keeps the current one of the redirect if the subquery returns
    #   NULL, i.e. the target does not exist in namespace 0 or has no Wikidata id itself;
    # - WHERE selects the redirect itself. Redirects that are not in the mapping table (not in
    #   namespace 0) match no row and are skipped.
    _logger.info("Parsing redirects dump")
    with conn:
        conn.executemany(
            """UPDATE mapping SET wikidata_id = COALESCE(
                (SELECT target.wikidata_id FROM mapping AS target WHERE target.wikipedia_title = ?),
                wikidata_id
            ) WHERE wikipedia_id = ?""",
            _parse_redirects(redirects_dump),
        )

    # Step 4: The index for `WikiMapper.id_to_titles` and `id_to_wikipedia_ids`. Created after all
    # Wikidata ids are set, which is faster than updating the index for every single change.
    _logger.info("Creating database index on 'wikidata_id'")
    with conn:
        conn.execute("""CREATE INDEX idx_wikidata_id ON mapping(wikidata_id);""")

    # Summary for the log: count(wikidata_id) counts the rows whose Wikidata id is not NULL
    total, mapped = conn.execute("SELECT count(*), count(wikidata_id) FROM mapping").fetchone()
    _logger.info("Index contains [%d] pages, [%d] of them mapped to Wikidata", total, mapped)

    conn.close()

    return path_to_db
