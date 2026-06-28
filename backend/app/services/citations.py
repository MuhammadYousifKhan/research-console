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

    The data model only carries ``title`` and ``url`` (no author or publication
    date), so every reference is a *web resource* citation: the site name is the
    URL host, the date is ``n.d.`` (no date), and an **accessed date** is added.
    Nothing is invented — this keeps the honest-state principle intact.
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

    # --- per-style formatters ------------------------------------------

    def _apa(self, source: Source) -> str:
        # Title. (n.d.). Site name. Retrieved Month D, Year, from URL
        parts = [f"{self._title(source)}.", "(n.d.).", f"{self._site_name(source)}."]
        if source.url:
            parts.append(f"Retrieved {self._accessed_long()}, from {source.url}")
        return " ".join(parts)

    def _mla(self, source: Source) -> str:
        # "Title." Site name, URL. Accessed D Month Year.
        ref = f'"{self._title(source)}." {self._site_name(source)}'
        if source.url:
            ref += f", {source.url}"
        ref += f". Accessed {self._accessed_day_first()}."
        return ref

    def _ieee(self, source: Source) -> str:
        # "Title," Site name. [Online]. Available: URL. [Accessed: DD-Mon-Year].
        ref = f'"{self._title(source)}," {self._site_name(source)}.'
        if source.url:
            ref += f" [Online]. Available: {source.url}."
        ref += f" [Accessed: {self._accessed_ieee()}]."
        return ref

    def _harvard(self, source: Source) -> str:
        # Site name (n.d.) Title. Available at: URL (Accessed: D Month Year).
        ref = f"{self._site_name(source)} (n.d.) {self._title(source)}."
        if source.url:
            ref += f" Available at: {source.url}"
        ref += f" (Accessed: {self._accessed_day_first()})."
        return ref

    def _chicago(self, source: Source) -> str:
        # "Title." Site name. Accessed Month D, Year. URL.
        ref = f'"{self._title(source)}." {self._site_name(source)}.'
        ref += f" Accessed {self._accessed_long()}."
        if source.url:
            ref += f" {source.url}."
        return ref

    def _bibtex(self, source: Source) -> str:
        key = f"source{source.citation_id}" if source.citation_id else "source"
        fields = [f"  title = {{{self._title(source)}}}"]
        if self._host(source.url):
            fields.append(f"  howpublished = {{{self._site_name(source)}}}")
        if source.url:
            fields.append(f"  url = {{{source.url}}}")
        fields.append(f"  note = {{Accessed: {self.accessed.isoformat()}}}")
        body = ",\n".join(fields)
        return f"@misc{{{key},\n{body}\n}}"
