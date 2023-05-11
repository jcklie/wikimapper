import pytest
from typing import List

BAVARIAN_PARAMS = [
    pytest.param("Stoaboog", "Q168327"),
    pytest.param("Wechslkrod", "Q243242"),
    pytest.param("Wickiana", "Q2567666"),
    pytest.param("Ulrich_Zwingli", "Q123034"),
    pytest.param("Jingstes_Gricht", "Q1821239"),
    pytest.param("Sånkt_Johann_im_Pongau", "Q251022", id="Has special character"),
    pytest.param("Quadrátkilometa", "Q25343", id="Has redirect"),
    pytest.param("D'_boarische_Woocha", "Q20616808", id="Has special character"),
    pytest.param("I am not in the Wiki", None, id="Title not in the wiki"),
    pytest.param("tungsten", None, id="In the index, but not mapped"),
]


@pytest.mark.parametrize("page_title, expected", BAVARIAN_PARAMS)
def test_title_to_id(bavarian_wiki_mapper, page_title: str, expected: str):
    mapper = bavarian_wiki_mapper

    wikidata_id = mapper.title_to_id(page_title)

    assert wikidata_id == expected


@pytest.mark.parametrize("page_title, expected", BAVARIAN_PARAMS)
def test_url_to_id(bavarian_wiki_mapper, page_title: str, expected: str):
    mapper = bavarian_wiki_mapper

    url = "https://bar.wikipedia.org/wiki/" + page_title
    wikidata_id = mapper.url_to_id(url)

    assert wikidata_id == expected


@pytest.mark.parametrize(
    "wikidata_id, expected",
    [
        ("Q1027119", ["Gallesium", "Gallese", "Gallesium_(Titularbistum)"]),
        ("Q102904", ["Vulkanologie", "Vuikanologie"]),
        ("Q160525", ['Brezn', 'Breze', 'Brezel', 'Brezen']),
        ("12345678909876543210", []),
    ],
)
def test_id_to_titles(bavarian_wiki_mapper, wikidata_id: str, expected: str):
    mapper = bavarian_wiki_mapper

    titles = mapper.id_to_titles(wikidata_id)

    assert set(titles) == set(expected)


@pytest.mark.parametrize(
    "wikipedia_id, expected",
    [
        (24520, "Q168327"),   # Stoaboog
        (8535, "Q243242"),    # Wechslkrod
        (32218, None),        # Wechslkrod, but namespace 1, so cannot be in the database
        (32176, "Q2567666"),  # Wickiana
        (32252, "Q123034"),   # Ulrich_Zwingli
        (32311, "Q1821239"),  # Jingstes_Gricht
        (2143, "Q251022"),    # Sånkt_Johann_im_Pongau
        (2217, "Q25343"),     # Quadrátkilometa
        (4209, "Q20616808"),  # D'_boarische_Woocha
        (1997, "Q160525"),    # Brezn
        (5740, None),         # Brezn, but namespace 1, so cannot be in the database
        (24100, "Q160525"),   # Brezel
        (28193, "Q160525"),   # Brezen
        (105208, "Q102904"),  # Vulkanologie
        (105288, "Q102904"),  # Vuikanologie
    ]
)
def test_wikipedia_id_to_id(bavarian_wiki_mapper, wikipedia_id: int, expected: str):
    mapper = bavarian_wiki_mapper

    wikidata_id = mapper.wikipedia_id_to_id(wikipedia_id)

    assert wikidata_id == expected


@pytest.mark.parametrize(
    "wikidata_id, expected",
    [
        ("Q1027119", [105563, 105564, 105565]),   # Gallesium, Gallese, Gallesium_(Titularbistum)
        ("Q102904", [105208, 105288]),            # Vulkanologie, Vuikanologie
        ("Q160525", [1997, 2778, 24100, 28193]),  # Brezn, Breze, Brezel, Brezen
        ("12345678909876543210", []),
    ]
)
def test_id_to_wikipedia_ids(bavarian_wiki_mapper, wikidata_id: str, expected: List[int]):
    mapper = bavarian_wiki_mapper

    wikipedia_ids = mapper.id_to_wikipedia_ids(wikidata_id)

    assert set(wikipedia_ids) == set(expected)


@pytest.mark.parametrize(
    "wikipedia_id, expected",
    [
        (24520, "Stoaboog"),
        (8535, "Wechslkrod"),
        (32218, None),  # Wechslkrod, but namespace 1, so cannot be in the database
        (32176, "Wickiana"),
        (32252, "Ulrich_Zwingli"),
        (32311, "Jingstes_Gricht"),
        (2143, "Sånkt_Johann_im_Pongau"),
        (2217, "Quadrátkilometa"),
        (4209, "D'_boarische_Woocha"),
        (1997, "Brezn"),
        (5740, None),  # Brezn, but namespace 1, so cannot be in the database
        (24100, "Brezel"),
        (28193, "Brezen"),
        (105208, "Vulkanologie"),
        (105288, "Vuikanologie"),
    ]
)
def test_wikipedia_id_to_title(bavarian_wiki_mapper, wikipedia_id: int, expected: str):
    mapper = bavarian_wiki_mapper

    title = mapper.wikipedia_id_to_title(wikipedia_id)

    assert title == expected


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Stoaboog", 24520),
        ("Wechslkrod", 8535),
        ("Wickiana", 32176),
        ("Ulrich_Zwingli", 32252),
        ("Jingstes_Gricht", 32311),
        ("Sånkt_Johann_im_Pongau", 2143),
        ("Quadrátkilometa", 2217),
        ("D'_boarische_Woocha", 4209),
        ("Brezn", 1997),
        ("Brezel", 24100),
        ("Brezen", 28193),
        ("Vulkanologie", 105208),
        ("Vuikanologie", 105288),
        ("xxxxxxxxxx", None),
    ]
)
def test_wikipedia_id_to_title(bavarian_wiki_mapper, title: str, expected: int):
    mapper = bavarian_wiki_mapper

    wikipedia_id = mapper.title_to_wikipedia_id(title)

    assert wikipedia_id == expected
