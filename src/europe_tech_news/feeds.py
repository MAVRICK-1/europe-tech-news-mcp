"""Feed registry for European tech news sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    region: str  # "eu", or a lowercase country/area code like "de", "fr", "uk", "nordics"
    topics: tuple[str, ...]  # e.g. ("startups", "funding")
    broad: bool = False  # general outlet: keep only articles that mention Europe
    weight: float = 1.0  # editorial weight used when ranking top news


FEEDS: tuple[Feed, ...] = (
    # Pan-European
    Feed("Tech.eu", "https://tech.eu/feed", "eu", ("startups", "funding", "general")),
    Feed("EU-Startups", "https://www.eu-startups.com/feed/", "eu", ("startups", "funding")),
    Feed("Sifted", "https://sifted.eu/feed", "eu", ("startups", "funding", "general")),
    Feed("The Next Web", "https://thenextweb.com/feed", "eu", ("general", "ai"), broad=True, weight=0.8),
    Feed("Euractiv", "https://www.euractiv.com/feed/", "eu", ("regulation", "policy", "ai"), broad=True, weight=1.2),
    Feed("European Commission Digital Strategy", "https://digital-strategy.ec.europa.eu/en/rss.xml", "eu", ("regulation", "policy", "ai", "cloud"), weight=1.3),
    Feed("Politico Europe Tech", "https://www.politico.eu/section/technology/feed/", "eu", ("regulation", "policy")),
    # UK and Ireland
    Feed("The Register", "https://www.theregister.com/headlines.atom", "uk", ("cloud", "security", "general")),
    Feed("Computer Weekly", "https://www.computerweekly.com/rss/All-Computer-Weekly-content.xml", "uk", ("enterprise", "cloud")),
    Feed("ITPro", "https://www.itpro.com/feeds/all", "uk", ("cloud", "security", "enterprise"), broad=True, weight=0.8),
    Feed("BBC Technology", "https://www.bbc.co.uk/news/technology/rss.xml", "uk", ("general",), broad=True, weight=1.1),
    Feed("The Guardian Technology", "https://www.theguardian.com/technology/rss", "uk", ("general", "regulation"), broad=True, weight=1.1),
    Feed("Silicon Republic", "https://www.siliconrepublic.com/feed", "ie", ("startups", "general")),
    # DACH
    Feed("Heise Online", "https://www.heise.de/rss/heise-atom.xml", "de", ("general", "security", "cloud")),
    Feed("Golem", "https://rss.golem.de/rss.php?feed=RSS2.0", "de", ("general", "security")),
    Feed("t3n", "https://t3n.de/rss.xml", "de", ("general", "startups", "ai")),
    Feed("Netzpolitik", "https://netzpolitik.org/feed/", "de", ("regulation", "policy", "security")),
    # France
    Feed("Maddyness", "https://www.maddyness.com/feed/", "fr", ("startups", "funding")),
    Feed("Silicon.fr", "https://www.silicon.fr/feed", "fr", ("enterprise", "cloud", "security")),
    Feed("Le Monde Informatique", "https://www.lemondeinformatique.fr/rss/rss.xml", "fr", ("enterprise", "cloud", "security")),
    # Netherlands / Benelux
    Feed("Silicon Canals", "https://siliconcanals.com/feed/", "nl", ("startups", "funding")),
    Feed("Computable", "https://www.computable.nl/feed/", "nl", ("enterprise", "cloud")),
    # Nordics
    Feed("Nordic9", "https://nordic9.com/feed/", "nordics", ("startups", "funding")),
    # Southern / Iberia
    Feed("Silicon Canals Spain", "https://siliconcanals.com/spain/feed/", "es", ("startups", "funding")),
    # Italy
    Feed("Il Sole 24 Ore Tecnologia", "https://www.ilsole24ore.com/rss/tecnologia.xml", "it", ("general",)),
)

REGION_ALIASES: dict[str, set[str]] = {
    "europe": {"eu", "uk", "ie", "de", "fr", "nl", "nordics", "es", "it"},
    "eu": {"eu"},
    "uk": {"uk", "ie"},
    "britain": {"uk", "ie"},
    "ireland": {"ie"},
    "dach": {"de"},
    "germany": {"de"},
    "france": {"fr"},
    "benelux": {"nl"},
    "netherlands": {"nl"},
    "nordics": {"nordics"},
    "scandinavia": {"nordics"},
    "iberia": {"es"},
    "spain": {"es"},
    "italy": {"it"},
}


def feeds_for(region: str | None, source: str | None = None) -> list[Feed]:
    """Return feeds matching a region alias (default: all of Europe)."""
    key = (region or "europe").strip().lower()
    codes = REGION_ALIASES.get(key, {key})
    selected = [f for f in FEEDS if f.region in codes or (key == "europe")]
    # Country-scoped requests still benefit from pan-European sources.
    if key not in ("europe", "eu"):
        selected += [f for f in FEEDS if f.region == "eu" and f not in selected]
    if source:
        s = source.strip().lower()
        selected = [f for f in selected if s in f.name.lower()]
    return selected
