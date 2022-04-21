from collections import namedtuple
import os

import pytest

from wikimapper import download_wikidumps, create_index, WikiMapper


Wiki = namedtuple("Wiki", ["dumpname", "path"])


@pytest.fixture(scope="package")
def bavarian_wiki_dump(tmpdir_factory) -> Wiki:
    """ We download the Bavarian Wiki, as it is quite small. """

    dumpname = "barwiki-latest"
    path = tmpdir_factory.mktemp("dumps").strpath
    download_wikidumps(dumpname, path)
    return Wiki(dumpname=dumpname, path=path)


@pytest.fixture(scope="package")
def bavarian_wiki_index(tmpdir_factory, bavarian_wiki_dump: Wiki) -> str:
    path_to_db = tmpdir_factory.mktemp("indices").join("index_barwiki-latest.db").strpath
    return create_index(bavarian_wiki_dump.dumpname, bavarian_wiki_dump.path, path_to_db)


@pytest.fixture
def bavarian_wiki_mapper(bavarian_wiki_index) -> WikiMapper:
    return WikiMapper(bavarian_wiki_index)
