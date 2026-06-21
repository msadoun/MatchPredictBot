from datetime import datetime
from email.utils import format_datetime
from xml.etree.ElementTree import Element, SubElement, tostring

import database as db
from config import BASE_URL


def _parse_iso(iso: str) -> datetime:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now()


def _rss_date(iso: str) -> str:
    return format_datetime(_parse_iso(iso))


def build_rss(feed: db.Feed, episodes: list[db.Episode]) -> bytes:
    rss = Element("rss", version="2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = feed.title
    SubElement(channel, "description").text = feed.description or feed.title
    SubElement(channel, "link").text = feed.source_url
    SubElement(channel, "language").text = "en"

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{BASE_URL}/feed/{feed.id}.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    if feed.thumbnail_url:
        SubElement(channel, "itunes:image").set("href", feed.thumbnail_url)
        image = SubElement(channel, "image")
        SubElement(image, "url").text = feed.thumbnail_url
        SubElement(image, "title").text = feed.title
        SubElement(image, "link").text = feed.source_url

    SubElement(channel, "itunes:author").text = "YouTube"
    SubElement(channel, "itunes:explicit").text = "no"

    for episode in episodes:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = episode.title
        SubElement(item, "description").text = episode.description or episode.title
        SubElement(item, "guid", {"isPermaLink": "false"}).text = episode.video_id
        SubElement(item, "pubDate").text = _rss_date(episode.published_at)
        SubElement(item, "link").text = (
            f"https://www.youtube.com/watch?v={episode.video_id}"
        )

        if episode.thumbnail_url:
            SubElement(item, "itunes:image").set("href", episode.thumbnail_url)

        if episode.duration_seconds:
            hours, rem = divmod(int(episode.duration_seconds), 3600)
            minutes, seconds = divmod(rem, 60)
            SubElement(item, "itunes:duration").text = (
                f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                if hours
                else f"{minutes:02d}:{seconds:02d}"
            )

        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", f"{BASE_URL}/audio/{episode.id}")
        enclosure.set("type", "audio/mpeg")
        if episode.duration_seconds:
            enclosure.set("length", str(int(episode.duration_seconds) * 16000))

    xml_decl = b'<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_decl + tostring(rss, encoding="utf-8")


def feed_url(feed_id: str) -> str:
    return f"{BASE_URL}/feed/{feed_id}.xml"
