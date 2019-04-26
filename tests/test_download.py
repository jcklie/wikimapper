import os

from wikimapper import download_wikidumps


def test_download(tmpdir):
    path = tmpdir.mkdir("download").strpath

    download_wikidumps("ndswiki-latest", path)
    files = os.listdir(path)

    expected = {
        "ndswiki-latest-redirect.sql.gz",
        "ndswiki-latest-page_props.sql.gz",
        "ndswiki-latest-page.sql.gz",
    }
    assert set(files) == expected

    for e in files:
        statinfo = os.stat(os.path.join(path, e))
        assert statinfo.st_size > 0, "[{0}] should be a non-empty file".format(e)
