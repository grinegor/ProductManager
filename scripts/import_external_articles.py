from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

try:
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"


@dataclass(frozen=True)
class Article:
    url: str
    category: str
    slug: str


ARTICLES = [
    Article("https://www.reforge.com/blog/how-to-price-your-ai-product", "growth", "reforge_how_to_price_your_ai_product"),
    Article("https://www.reforge.com/blog/four-fits-growth-framework", "growth", "reforge_four_fits_growth_framework"),
    Article("https://www.reforge.com/blog/ai-impact-product-management", "growth", "reforge_ai_impact_product_management"),
    Article("https://www.lennysnewsletter.com/p/what-is-a-good-activation-rate", "growth", "lenny_what_is_a_good_activation_rate"),
    Article("https://www.revenuecat.com/blog/growth/free-trials-dont-make-sense-anymore/", "growth", "revenuecat_free_trials_dont_make_sense_anymore"),
    Article("https://www.revenuecat.com/blog/growth/7-day-trial-subscription-app/", "growth", "revenuecat_7_day_trial_subscription_app"),
    Article("https://www.revenuecat.com/blog/growth/ad-monetization-subscription-apps/", "growth", "revenuecat_ad_monetization_subscription_apps"),
    Article("https://www.revenuecat.com/blog/company/paywalls-on-the-web/", "growth", "revenuecat_paywalls_on_the_web"),
    Article("https://www.revenuecat.com/blog/engineering/announcing-paywall-rules-show-or-hide-paywall-components/", "growth", "revenuecat_paywall_rules_show_or_hide_components"),
    Article("https://www.revenuecat.com/blog/growth/weird-paywalls-drive-subscription-growth", "growth", "revenuecat_weird_paywalls_drive_subscription_growth"),
    Article("https://www.purchasely.com/blog/how-to-create-a-success-in-a-crowded-market-with-belen-caeiro-babbel", "growth", "purchasely_success_in_a_crowded_market_babbel"),
    Article("https://www.purchasely.com/blog/how-to-monetize-your-app-expert-tips-from-steve-p.-young-app-masters", "growth", "purchasely_monetize_your_app_steve_young"),
    Article("https://rockhealth.com/insights/the-tortoise-and-the-hare-of-care-health-ai-insights-from-rock-healths-2025-consumer-adoption-survey/", "competitors", "rock_health_health_ai_consumer_adoption_survey_2025"),
    Article("https://rockhealth.com/insights/reflections-on-a-decade-of-digital-health-a-conversation-with-halle-tecco/", "competitors", "rock_health_reflections_on_a_decade_of_digital_health"),
    Article("https://rockhealth.com/insights/2025-year-end-digital-health-funding-overview-a-tale-of-two-markets/", "competitors", "rock_health_2025_year_end_digital_health_funding"),
    Article("https://rockhealth.com/insights/healthcare-innovation-at-the-turn-of-2026-mapping-whats-now-and-whats-next-in-digital-health/", "competitors", "rock_health_healthcare_innovation_turn_of_2026"),
    Article("https://rockhealth.com/insights/women-in-focus-understanding-women-as-digital-health-consumers/", "competitors", "rock_health_women_as_digital_health_consumers"),
    Article("https://a16z.com/infinite-healthcare-whats-it-worth/", "competitors", "a16z_infinite_healthcare_whats_it_worth"),
    Article("https://a16z.com/its-time-to-build-healthtech-infrastructure/", "competitors", "a16z_its_time_to_build_healthtech_infrastructure"),
    Article("https://review.firstround.com/servals-path-to-product-market-fit/", "competitors", "first_round_servals_path_to_product_market_fit"),
]


NOISE_PATTERNS = [
    r"^Book a demo$",
    r"^Login$",
    r"^Sign in$",
    r"^Subscribe$",
    r"^Resources$",
    r"^Company$",
    r"^Solution$",
    r"^Documentation$",
    r"^Help Center$",
    r"^See the Paywall Builder in action$",
]


def strip_html_to_text(html_text: str) -> str:
    without_script = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S | re.I)
    without_style = re.sub(r"<style.*?</style>", " ", without_script, flags=re.S | re.I)
    no_tags = re.sub(r"<[^>]+>", " ", without_style)
    unescaped = html.unescape(no_tags)
    compact = re.sub(r"\s+", " ", unescaped).strip()
    return compact


def cleanup_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n")]
    cleaned: list[str] = []

    for line in lines:
        if not line:
            continue
        if len(line) < 3:
            continue
        if any(re.match(pattern, line, flags=re.I) for pattern in NOISE_PATTERNS):
            continue
        cleaned.append(line)

    merged = "\n".join(cleaned)
    merged = re.sub(r"\n{3,}", "\n\n", merged)
    merged = merged.replace("\u00a0", " ")
    return merged.strip()


def shorten_words(text: str, max_words: int = 2200) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "\n\n[Truncated to keep KB compact.]"


def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    response = requests.get(url, timeout=45, headers=headers)
    response.raise_for_status()
    return response.text


def extract_with_trafilatura(url: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if trafilatura is None:
        return None, None, None

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None, None, None

    extracted = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )

    metadata = trafilatura.extract_metadata(downloaded)
    title = metadata.title.strip() if metadata and metadata.title else None
    published = metadata.date.strip() if metadata and metadata.date else None

    return extracted, title, published


def extract_title_from_html(html_text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html_text, flags=re.S | re.I)
    if not match:
        return "Untitled Article"
    title = html.unescape(match.group(1))
    title = re.sub(r"\s+", " ", title).strip()
    return title


def import_article(article: Article) -> tuple[Path, int, str]:
    html_text = fetch_html(article.url)

    extracted, title, published = extract_with_trafilatura(article.url)

    method = "trafilatura"
    if not extracted or len(extracted.split()) < 180:
        method = "html_fallback"
        extracted = strip_html_to_text(html_text)

    body = cleanup_text(extracted)
    body = shorten_words(body, max_words=2200)

    final_title = title or extract_title_from_html(html_text)
    published = published or "unknown"

    out_dir = DOCS_DIR / article.category
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{article.slug}.md"

    imported_at = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")

    content = (
        f"# {final_title}\n\n"
        f"Source: {article.url}\n"
        f"Imported: {imported_at}\n"
        f"Published: {published}\n"
        f"Category: {article.category}\n"
        f"Extraction method: {method}\n\n"
        f"## Extracted Notes\n\n"
        f"{body}\n"
    )

    out_path.write_text(content, encoding="utf-8")
    return out_path, len(body.split()), method


def main() -> None:
    successes = 0
    failures = 0

    for article in ARTICLES:
        try:
            out_path, words, method = import_article(article)
            successes += 1
            print(f"OK  [{article.category}] {out_path.name} | {words} words | {method}")
        except Exception as exc:
            failures += 1
            print(f"ERR [{article.category}] {article.url} -> {exc}")

    print(f"\\nDone. Imported: {successes}, Failed: {failures}")


if __name__ == "__main__":
    main()
