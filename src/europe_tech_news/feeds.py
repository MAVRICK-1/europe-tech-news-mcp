"""Feed registry for European tech news sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feed:
    name: str
    url: str
    region: str  # "eu", or a lowercase country/area code like "de", "fr", "uk", "nordics"
    topics: tuple[str, ...]  # e.g. ("startups", "funding")


FEEDS: tuple[Feed, ...] = (
    # Pan-European
    Feed("Tech.eu", "https://tech.eu/feed", "eu", ("startups", "funding", "general")),
    Feed("EU-Startups", "https://www.eu-startups.com/feed/", "eu", ("startups", "funding")),
    Feed("Sifted", "https://sifted.eu/feed", "eu", ("startups", "funding", "general")),
    Feed("The Next Web", "https://thenextweb.com/feed", "eu", ("general", "ai")),
    Feed("Euractiv Tech", "https://www.euractiv.com/sections/digital/feed/", "eu", ("regulation", "policy", "ai")),
    Feed("Politico Europe Tech", "https://www.politico.eu/section/technology/feed/", "eu", ("regulation", "policy")),
    # UK and Ireland
    Feed("The Register", "https://www.theregister.com/headlines.atom", "uk", ("cloud", "security", "general")),
    Feed("Computer Weekly", "https://www.computerweekly.com/rss/All-Computer-Weekly-content.xml", "uk", ("enterprise", "cloud")),
    Feed("Silicon Republic", "https://www.siliconrepublic.com/feed", "ie", ("startups", "general")),
    # DACH
    Feed("Heise Online", "https://www.heise.de/rss/heise-atom.xml", "de", ("general", "security", "cloud")),
    # France
    Feed("Maddyness", "https://www.maddyness.com/feed/", "fr", ("startups", "funding")),
    # Netherlands / Benelux
    Feed("Silicon Canals", "https://siliconcanals.com/feed/", "nl", ("startups", "funding")),
    # Nordics
    Feed("Nordic9", "https://nordic9.com/feed/", "nordics", ("startups", "funding")),
    # Southern / Iberia
    Feed("Silicon Canals Spain", "https://siliconcanals.com/spain/feed/", "es", ("startups", "funding")),
)

REGION_ALIASES: dict[str, set[str]] = {
    "europe": {"eu", "uk", "ie", "de", "fr", "nl", "nordics", "es"},
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
