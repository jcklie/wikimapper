import argparse
import logging
import os

from wikimapper.__version__ import __version__
from wikimapper import download_wikidumps, create_index, WikiMapper


def main():
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    description = "Map Wikipedia page titles to Wikidata IDs and vice versa."
    parser = argparse.ArgumentParser(description=description)

    subparsers = parser.add_subparsers(help="sub-command help", dest="command")

    # Downloda parser
    parser_download = subparsers.add_parser(
        "download", help="Download Wikipedia dumps for creating a custom index."
    )
    parser_download.add_argument(
        "dumpname",
        type=_dump_name,
        help='Name of the Wikipedia dump, e.g. "enwiki-latest" for the latest English Wikipedia dump or "barwiki-20190420" for a dump from the Bavarian Wikipedia taken at the 20th April, 2019',
    )
    parser_download.add_argument(
        "--overwrite",
        action="store_true",
        help='Overwrite existing files if they already exist (default: "False")',
    )
    parser_download.add_argument(
        "--dir",
        type=_dir_path,
        default=os.getcwd(),
        help="Path to the folder in which the dump should be stored (default: current directory)",
    )
    parser_download.add_argument(
        "--mirror",
        type=str,
        default="https://dumps.wikimedia.org",
        help='URL of the Wikipedia dump mirror to use (default: "https://dumps.wikimedia.org")',
    )

    # Index creation parser
    parser_create = subparsers.add_parser(
        "create", help="Use a previously downloaded Wikipedia dump to create a custom index."
    )
    parser_create.add_argument(
        "dumpname",
        type=_dump_name,
        help='Name of the Wikipedia dump, e.g. "enwiki-latest" for the latest English Wikipedia dump or "barwiki-20190420" for a dump from the Bavarian Wikipedia taken at the 20th April, 2019',
    )
    parser_create.add_argument(
        "--target",
        default=None,
        type=str,
        help='Path and name of the index to create (default: "index_${dumpname}.db")',
    )
    parser_create.add_argument(
        "--dumpdir",
        type=_dir_path,
        default=os.getcwd(),
        help="Path to the folder in which the dump was stored (default: current directory)",
    )

    # Mapping parser
    parser_title_to_id = subparsers.add_parser(
        "title2id", help="Map a Wikipedia title to a Wikidata ID."
    )
    parser_title_to_id.add_argument(
        "index", type=str, help="Path to the index file that shall be used for the mapping."
    )
    parser_title_to_id.add_argument(
        "title",
        type=str,
        help="Page title to map. Spaces are replaced by underscores, the title should not be escaped.",
    )

    parser_url_to_id = subparsers.add_parser("url2id", help="Map a Wikipedia URL to a Wikidata ID.")
    parser_url_to_id.add_argument(
        "index", type=str, help="Path to the index file that shall be used for the mapping."
    )
    parser_url_to_id.add_argument(
        "url",
        type=str,
        help="URL to map. It is not checked whether the URL comes from the same Wiki as the index.",
    )

    parser_id_to_title = subparsers.add_parser(
        "id2titles", help="Map a Wikidata ID to one or more Wikipedia titles."
    )
    parser_id_to_title.add_argument(
        "index", type=str, help="Path to the index file that shall be used for the mapping."
    )
    parser_id_to_title.add_argument("id", type=str, help="Wikidata ID to map.")

    # Version
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

    # Do the work
    args = parser.parse_args()

    if args.command == "download":
        download_wikidumps(args.dumpname, args.dir, args.mirror, args.overwrite)
    elif args.command == "create":
        create_index(args.dumpname, args.dumpdir, args.target)
    elif args.command == "title2id":
        mapper = WikiMapper(args.index)
        result = mapper.title_to_id(args.title)
        if result:
            print(result)
    elif args.command == "url2id":
        mapper = WikiMapper(args.index)
        result = mapper.url_to_id(args.url)
        if result:
            print(result)
    elif args.command == "id2titles":
        mapper = WikiMapper(args.index)
        results = mapper.id_to_titles(args.id)
        for result in results:
            print(result)
    else:
        parser.print_help()


def _dir_path(path) -> str:
    """ Checks whether `path` is a valid path to a directory. """
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path to a directory!")


def _dump_name(name) -> str:
    """ Checks whether `name` is a valid Wikipedia dump name. """
    parts = name.split("-")
    err = lambda: argparse.ArgumentTypeError(f"dumpname: [{name}] is not a valid dump name")

    if len(parts) != 2:
        raise err()

    wikiname, date = parts
    if not wikiname.endswith("wiki"):
        raise err()

    return name
