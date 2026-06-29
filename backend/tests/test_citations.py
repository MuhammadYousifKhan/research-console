from datetime import date

from app.schemas.research import Source
from app.services.citations import CitationFormatter

ACCESSED = date(2026, 6, 29)


def _academic() -> Source:
    return Source(
        citation_id=1,
        title="Attention Is All You Need",
        url="https://arxiv.org/abs/1706.03762",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        year=2017,
        source_type="academic",
        reliability="high",
    )


def _web() -> Source:
    return Source(
        citation_id=2,
        title="What is machine learning",
        url="https://www.example.com/ml",
        source_type="news",
    )


def test_academic_citations_use_authors_and_year():
    fmt = CitationFormatter(accessed=ACCESSED)

    apa = fmt.format(_academic(), "apa")
    assert apa.startswith("Vaswani, A., Shazeer, N., & Parmar, N. (2017).")
    assert "n.d." not in apa

    ieee = fmt.format(_academic(), "ieee")
    assert ieee.startswith('A. Vaswani, N. Shazeer, and N. Parmar, "Attention Is All You Need," arxiv.org, 2017.')

    harvard = fmt.format(_academic(), "harvard")
    assert harvard.startswith("Vaswani, A., Shazeer, N. and Parmar, N. (2017)")

    mla = fmt.format(_academic(), "mla")
    assert mla.startswith('Vaswani, Ashish, Noam Shazeer, and Niki Parmar. "Attention Is All You Need."')

    bibtex = fmt.format(_academic(), "bibtex")
    assert "author = {Ashish Vaswani and Noam Shazeer and Niki Parmar}" in bibtex
    assert "year = {2017}" in bibtex


def test_web_sources_keep_web_resource_style():
    fmt = CitationFormatter(accessed=ACCESSED)

    apa = fmt.format(_web(), "apa")
    assert "(n.d.)" in apa
    assert "Vaswani" not in apa

    bibtex = fmt.format(_web(), "bibtex")
    assert "author =" not in bibtex
    assert "year =" not in bibtex


def test_many_authors_collapse_to_et_al():
    source = _academic().model_copy(update={"authors": [f"Given{i} Surname{i}" for i in range(10)]})
    fmt = CitationFormatter(accessed=ACCESSED)

    assert "et al." in fmt.format(source, "apa")
    assert "et al." in fmt.format(source, "ieee")
    assert "et al." in fmt.format(source, "mla")


def test_format_all_covers_every_style():
    fmt = CitationFormatter(accessed=ACCESSED)
    styles = fmt.format_all([_academic(), _web()])

    assert set(styles) == {"apa", "mla", "ieee", "harvard", "chicago", "bibtex"}
    for items in styles.values():
        assert len(items) == 2
        assert all(item.text for item in items)
