import logging
import os
import shutil
import sys
import urllib.parse
import urllib.request

_logger = logging.getLogger(__name__)


def _report_hook(count: int, block_size: int, total_size: int):
    percent = min(int(count * block_size * 100 / total_size), 100)
    sys.stdout.write("\r%2d%%" % percent)


def _download_file(url: str, target: str, overwrite: bool):
    """ Downloads the content identified by `url` and saves it in `target`."""
    if os.path.exists(target) and not overwrite:
        _logger.info("[%s] already exists, skipping downloading [%s]!", target, url)
        return

    _logger.info("Downloading [%s] to [%s]", url, target)

    local_name, _ = urllib.request.urlretrieve(url, reporthook=_report_hook)
    sys.stdout.write("\r")
    shutil.move(local_name, target)


def download_wikidumps(
    dumpname: str, path: str, mirror: str = "https://dumps.wikimedia.org/", overwrite: bool = False
):
    """ Downloads pages, page props and redirect SQL dumps for the dump
    specified by `dumpname` to the folder `path`. If `overwrite` is true,
    then it is downloaded again even if the files already exist.

    Args:
        dumpname (str): The name of the dump, e.g. `enwiki-latest` or `barwiki-20190420`.
        path (str): Path to the folder where the dumps should be downloaded to.
        mirror (str): The Wikipedia mirror to download from. Defaults to `https://dumps.wikimedia.org/`.
        overwrite (bool): If true, then overwrite existing files, else, do not download again. Defaults to `False`.

    """
    os.makedirs(path, exist_ok=True)

    wiki_name, date = dumpname.split("-")

    url = urllib.parse.urljoin(mirror, wiki_name) + "/" + date + "/"

    pages_dump = dumpname + "-page.sql.gz"
    page_props_dump = dumpname + "-page_props.sql.gz"
    redirects_dump = dumpname + "-redirect.sql.gz"

    for dump in [pages_dump, page_props_dump, redirects_dump]:
        _download_file(url + dump, os.path.join(path, dump), overwrite)
