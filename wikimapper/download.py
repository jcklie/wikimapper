import logging
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request

from wikimapper.__version__ import __version__

_logger = logging.getLogger(__name__)

# Wikimedia rejects requests with generic user agents like `Python-urllib/3.x` (HTTP 403), see
# https://meta.wikimedia.org/wiki/User-Agent_policy
USER_AGENT = "wikimapper/{0} (https://github.com/jcklie/wikimapper)".format(__version__)

# Seconds to wait for the server to connect or to send the next block. Without it, a server that
# accepts the request but stops sending data makes the download wait forever.
_TIMEOUT = 60


def _report_hook(count: int, block_size: int, total_size: int):
    percent = min(int(count * block_size * 100 / total_size), 100)
    sys.stdout.write("\r%2d%%" % percent)


def _download_file(url: str, target: str, overwrite: bool):
    """Downloads the content identified by `url` and saves it in `target`."""
    if os.path.exists(target) and not overwrite:
        _logger.info("[%s] already exists, skipping downloading [%s]!", target, url)
        return

    _logger.info("Downloading [%s] to [%s]", url, target)

    # Same as `urllib.request.urlretrieve`, which cannot set the user agent of a single request.
    # Set the user agent on this request only, instead of installing a global opener, which would
    # also change the requests of every other code in the same process
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    # Open the connection; raises `HTTPError` for responses like 403 or 404. The timeout applies to
    # every single network operation, not to the whole download, so large dumps are not affected.
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        # Download into a temporary file first, so `target` only appears once the download is
        # complete; `delete=False` keeps the file after closing so that it can be moved
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Remember the path of the temporary file for the move (or the error) below
            local_name = f.name
            # Read in blocks of 8 KiB, the same block size `urlretrieve` uses
            block_size = 8192
            # Expected size in bytes from the server, or -1 if it did not send one
            total_size = int(response.headers.get("Content-Length", -1))
            # Number of bytes received so far
            read = 0
            # Number of blocks received so far, passed to the progress hook
            count = 0
            # Report 0% before the first block arrives, as `urlretrieve` does
            _report_hook(count, block_size, total_size)
            # Copy the response into the temporary file block by block
            while True:
                # Read the next block; an empty result means the server has sent everything
                block = response.read(block_size)
                if not block:
                    break
                # Append the block to the temporary file
                f.write(block)
                # Count the bytes that were actually received; the last block may be shorter
                read += len(block)
                # Count the block and update the progress shown on the console
                count += 1
                _report_hook(count, block_size, total_size)

    # The connection ended before all announced bytes arrived: fail instead of keeping a
    # truncated dump. The incomplete temporary file is never moved to `target`.
    if read < total_size:
        raise urllib.error.ContentTooShortError(
            "retrieval incomplete: got only %i out of %i bytes" % (read, total_size),
            # Same content as `urlretrieve` attaches: the temporary file and the response headers
            (local_name, response.headers),
        )

    sys.stdout.write("\r")
    shutil.move(local_name, target)


def download_wikidumps(
    dumpname: str, path: str, mirror: str = "https://dumps.wikimedia.org/", overwrite: bool = False
):
    """Downloads pages, page props and redirect SQL dumps for the dump
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

    # Not `urljoin`, as that drops the last path segment of mirrors like `https://host/dumps`
    url = mirror.rstrip("/") + "/" + wiki_name + "/" + date + "/"

    pages_dump = dumpname + "-page.sql.gz"
    page_props_dump = dumpname + "-page_props.sql.gz"
    redirects_dump = dumpname + "-redirect.sql.gz"

    for dump in [pages_dump, page_props_dump, redirects_dump]:
        _download_file(url + dump, os.path.join(path, dump), overwrite)
