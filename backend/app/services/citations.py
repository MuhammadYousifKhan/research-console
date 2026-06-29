from datetime import date
from urllib.parse import urlparse

from app.schemas.research import CitationItem, CitationStyle, Source

# Styles exposed by the citation export, in display order.
CITATION_STYLES: tuple[CitationStyle, ...] = (
    "apa",
    "mla",
    "ieee",
    "harvard",
    "chicago",
    "bibtex",
)


class CitationFormatter:
    """Deterministically render a cleaned ``Source`` as a reference string.

    When a ``Source`` carries bibliographic metadata (``authors`` and/or
    ``year`` — populated by the academic tools), references use a proper
    author-year citation. Web sources without that metadata fall back to a
    *web resource* citation: the site name is the URL host, the date is
    ``n.d.`` (no date), and an **accessed date** is added. Nothing is invented
    — this keeps the honest-state principle intact.
    """

    def __init__(self, accessed: date | None = None) -> None:
        self.accessed = accessed or date.today()

    # --- public API -----------------------------------------------------

    def format(self, source: Source, style: CitationStyle) -> str:
        formatter = getattr(self, f"_{style}")
        return formatter(source)

    def format_all(self, sources: list[Source]) -> dict[CitationStyle, list[CitationItem]]:
        return {
            style: [
                CitationItem(
                    citation_id=source.citation_id,
                    title=source.title,
                    url=source.url,
                    text=self.format(source, style),
                )
                for source in sources
            ]
            for style in CITATION_STYLES
        }

    # --- helpers --------------------------------------------------------

    def _host(self, url: str) -> str:
        if not url:
            return ""
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc

    def _site_name(self, source: Source) -> str:
        return self._host(source.url) or "Unknown source"

    def _title(self, source: Source) -> str:
        return (source.title or "Untitled source").strip().rstrip(".")

    def _accessed_long(self) -> str:
        # "June 28, 2026" — built manually to avoid platform-specific strftime flags.
        return f"{self.accessed.strftime('%B')} {self.accessed.day}, {self.accessed.year}"

    def _accessed_day_first(self) -> str:
        # "28 June 2026"
        return f"{self.accessed.day} {self.accessed.strftime('%B')} {self.accessed.year}"

    def _accessed_ieee(self) -> str:
        # "28-Jun-2026"
        return f"{self.accessed.day:02d}-{self.accessed.strftime('%b')}-{self.accessed.year}"

    # --- author / date helpers -----------------------------------------
    #
    # Sources that carry no bibliographic metadata (every web result today)
    # keep the original web-resource rendering: no author block and ``n.d.``.
    # Academic sources (arXiv, Semantic Scholar) populate ``authors``/``year``,
    # so the formatters below switch to a proper author-year citation. Beyond
    # ET_AL_THRESHOLD authors the list is collapsed to "first author et al."

    ET_AL_THRESHOLD = 6

    def _year(self, source: Source) -> str:
        return str(source.year) if source.year else "n.d."

    def _split_name(self, name: str) -> tuple[list[str], str]:
        # Assumes "Given [Middle ...] Surname" order (what arXiv/S2 return).
        # Periods are dropped so existing initials ("J.") collapse cleanly.
        tokens = [token for token in name.replace(".", " ").split() if token]
        if not tokens:
            return [], ""
        if len(tokens) == 1:
            return [], tokens[0]
        return tokens[:-1], tokens[-1]

    def _surname_initials(self, name: str) -> str:
        # "Ashish Vaswani" -> "Vaswani, A."
        given, surname = self._split_name(name)
        initials = " ".join(f"{token[0]}." for token in given if token)
        return f"{surname}, {initials}" if initials else surname

    def _initials_surname(self, name: str) -> str:
        # "Ashish Vaswani" -> "A. Vaswani"
        given, surname = self._split_name(name)
        initials = " ".join(f"{token[0]}." for token in given if token)
        return f"{initials} {surname}".strip()

    def _surname_given(self, name: str) -> str:
        # "Ashish Vaswani" -> "Vaswani, Ashish"
        given, surname = self._split_name(name)
        return f"{surname}, {' '.join(given)}".strip().rstrip(",") if given else surname

    def _given_surname(self, name: str) -> str:
        # "Ashish Vaswani" -> "Ashish Vaswani" (as given)
        given, surname = self._split_name(name)
        return f"{' '.join(given)} {surname}".strip()

    def _join_authors(self, names: list[str], last_sep: str) -> str:
        if len(names) == 1:
            return names[0]
        return f"{', '.join(names[:-1])}{last_sep}{names[-1]}"

    def _apa_authors(self, authors: list[str]) -> str:
        if len(authors) > self.ET_AL_THRESHOLD:
            return f"{self._surname_initials(authors[0])}, et al."
        return self._join_authors([self._surname_initials(a) for a in authors], ", & ")

    def _harvard_authors(self, authors: list[str]) -> str:
        if len(authors) > self.ET_AL_THRESHOLD:
            return f"{self._surname_initials(authors[0])} et al."
        return self._join_authors([self._surname_initials(a) for a in authors], " and ")

    def _ieee_authors(self, authors: list[str]) -> str:
        if len(authors) > self.ET_AL_THRESHOLD:
            return f"{self._initials_surname(authors[0])} et al."
        return self._join_authors([self._initials_surname(a) for a in authors], ", and ")

    def _mla_chicago_authors(self, authors: list[str]) -> str:
        # MLA/Chicago: first author inverted, the rest natural order; 4+ -> et al.
        if len(authors) > 3:
            return f"{self._surname_given(authors[0])}, et al."
        formatted = [self._surname_given(authors[0])] + [self._given_surname(a) for a in authors[1:]]
        return self._join_authors(formatted, ", and " if len(formatted) > 2 else " and ")

    # --- per-style formatters ------------------------------------------

    def _apa(self, source: Source) -> str:
        # With authors:  Authors (Year). Title. Site. Retrieved ..., from URL
        # Web fallback:   Title. (n.d.). Site. Retrieved ..., from URL
        if source.authors:
            parts = [f"{self._apa_authors(source.authors)} ({self._year(source)}).", f"{self._title(source)}.", f"{self._site_name(source)}."]
        else:
            parts = [f"{self._title(source)}.", f"({self._year(source)}).", f"{self._site_name(source)}."]
        if source.url:
            parts.append(f"Retrieved {self._accessed_long()}, from {source.url}")
        return " ".join(parts)

    def _mla(self, source: Source) -> str:
        # [Authors.] "Title." Site name[, Year], URL. Accessed D Month Year.
        lead = f"{self._mla_chicago_authors(source.authors)}. " if source.authors else ""
        ref = f'{lead}"{self._title(source)}." {self._site_name(source)}'
        if source.year:
            ref += f", {source.year}"
        if source.url:
            ref += f", {source.url}"
        ref += f". Accessed {self._accessed_day_first()}."
        return ref

    def _ieee(self, source: Source) -> str:
        # [Authors, ]"Title," Site name[, Year]. [Online]. Available: URL. [Accessed: DD-Mon-Year].
        lead = f"{self._ieee_authors(source.authors)}, " if source.authors else ""
        ref = f'{lead}"{self._title(source)}," {self._site_name(source)}'
        if source.year:
            ref += f", {source.year}"
        ref += "."
        if source.url:
            ref += f" [Online]. Available: {source.url}."
        ref += f" [Accessed: {self._accessed_ieee()}]."
        return ref

    def _harvard(self, source: Source) -> str:
        # Authors|Site (Year) Title. Available at: URL (Accessed: D Month Year).
        head = self._harvard_authors(source.authors) if source.authors else self._site_name(source)
        ref = f"{head} ({self._year(source)}) {self._title(source)}."
        if source.url:
            ref += f" Available at: {source.url}"
        ref += f" (Accessed: {self._accessed_day_first()})."
        return ref

    def _chicago(self, source: Source) -> str:
        # [Authors.] "Title." Site name[, Year]. Accessed Month D, Year. URL.
        lead = f"{self._mla_chicago_authors(source.authors)}. " if source.authors else ""
        ref = f'{lead}"{self._title(source)}." {self._site_name(source)}'
        if source.year:
            ref += f", {source.year}"
        ref += "."
        ref += f" Accessed {self._accessed_long()}."
        if source.url:
            ref += f" {source.url}."
        return ref

    def _bibtex(self, source: Source) -> str:
        key = f"source{source.citation_id}" if source.citation_id else "source"
        fields = []
        if source.authors:
            # BibTeX author lists are joined with " and ", names kept as given.
            fields.append(f"  author = {{{' and '.join(source.authors)}}}")
        fields.append(f"  title = {{{self._title(source)}}}")
        if source.year:
            fields.append(f"  year = {{{source.year}}}")
        if self._host(source.url):
            fields.append(f"  howpublished = {{{self._site_name(source)}}}")
        if source.url:
            fields.append(f"  url = {{{source.url}}}")
        fields.append(f"  note = {{Accessed: {self.accessed.isoformat()}}}")
        body = ",\n".join(fields)
        return f"@misc{{{key},\n{body}\n}}"
