import pytest

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
        ("Q10296976", ["Stootsfiahra_52", "Liste_der_Staatsoberhäupter_52"]),
        ("12345678909876543210", []),
    ],
)
def test_id_to_titles(bavarian_wiki_mapper, wikidata_id: str, expected: str):
    mapper = bavarian_wiki_mapper

    titles = mapper.id_to_titles(wikidata_id)

    assert set(titles) == set(expected)
