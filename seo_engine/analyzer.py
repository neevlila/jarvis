"""
Deterministic SEO Analyzer for J.A.R.V.I.S. SEO Intelligence.

Executes observable, evidence-grounded inspections across:
1. Technical SEO & Metadata
2. Headings & Document Structure
3. Image Optimization & Alt Semantics
4. Internal & External Link Quality
5. Social Metadata (OpenGraph & Twitter Cards)
6. Structured Data (JSON-LD & Schema.org)
7. Performance & Resource Signals
8. Accessibility Baseline Signals
9. Security Signals & Mixed Content
10. On-Page Content & Target Keyword Analysis
"""

import re
import json
import urllib.parse
from html.parser import HTMLParser
from typing import Dict, List, Any, Optional, Tuple, Set

from seo_engine.models import (
    SEOFinding,
    FindingSeverity,
    SEOCategory,
    EvidenceType,
    PerformanceSignalsData
)
from seo_engine.fetcher import FetchResult


class DOMCollector(HTMLParser):
    """
    Lightweight, robust SAX-style HTML parser extracting semantic elements,
    attributes, headings, images, links, scripts, and structured data blocks.
    """

    def __init__(self):
        super().__init__()
        self.doctype: Optional[str] = None
        self.html_attrs: Dict[str, str] = {}
        self.head_open = False
        self.body_open = False
        self.title_text: Optional[str] = None
        self.meta_tags: List[Dict[str, str]] = []
        self.link_tags: List[Dict[str, str]] = []
        self.headings: List[Dict[str, Any]] = []  # tag, text, attrs
        self.images: List[Dict[str, str]] = []    # src, alt, role, loading, width, height, aria-hidden
        self.links: List[Dict[str, Any]] = []     # href, text, target, rel, aria-label
        self.scripts: List[Dict[str, str]] = []   # src, type, content
        self.styles: List[Dict[str, str]] = []
        self.semantic_tags: Set[str] = set()
        self.form_inputs: List[Dict[str, str]] = []
        self.form_labels: List[str] = []
        self.buttons: List[Dict[str, str]] = []
        self.text_chunks: List[str] = []
        self.comments: List[str] = []

        self._curr_tag: Optional[str] = None
        self._curr_text: List[str] = []
        self._curr_attrs: Dict[str, str] = {}
        self._inside_script = False
        self._inside_script_type = ""
        self._inside_style = False
        self._inside_title = False
        self._inside_heading = False
        self._inside_link = False
        self._curr_link_data: Dict[str, Any] = {}

    def handle_decl(self, decl: str):
        if "doctype" in decl.lower():
            self.doctype = decl

    def handle_comment(self, data: str):
        self.comments.append(data)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        tag_lower = tag.lower()

        if tag_lower == "html":
            self.html_attrs = attr_dict
        elif tag_lower == "head":
            self.head_open = True
        elif tag_lower == "body":
            self.body_open = True
        elif tag_lower == "meta":
            self.meta_tags.append(attr_dict)
        elif tag_lower == "link":
            self.link_tags.append(attr_dict)
        elif tag_lower == "title":
            self._inside_title = True
            self._curr_text = []
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._inside_heading = True
            self._curr_tag = tag_lower
            self._curr_attrs = attr_dict
            self._curr_text = []
        elif tag_lower == "img":
            self.images.append(attr_dict)
        elif tag_lower == "a":
            self._inside_link = True
            self._curr_link_data = {
                "href": attr_dict.get("href", ""),
                "rel": attr_dict.get("rel", ""),
                "target": attr_dict.get("target", ""),
                "aria-label": attr_dict.get("aria-label", ""),
                "title": attr_dict.get("title", ""),
                "text": ""
            }
            self._curr_text = []
        elif tag_lower == "script":
            self._inside_script = True
            self._inside_script_type = attr_dict.get("type", "").lower()
            self._curr_attrs = attr_dict
            self._curr_text = []
        elif tag_lower == "style":
            self._inside_style = True
            self._curr_text = []
        elif tag_lower in ("header", "nav", "main", "footer", "article", "section", "aside"):
            self.semantic_tags.add(tag_lower)
        elif tag_lower in ("input", "textarea", "select"):
            self.form_inputs.append(attr_dict)
        elif tag_lower == "label":
            self.form_labels.append(attr_dict.get("for", ""))
        elif tag_lower == "button":
            self.buttons.append(attr_dict)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        if tag_lower == "title":
            self._inside_title = False
            self.title_text = "".join(self._curr_text).strip()
            self._curr_text = []
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6") and self._inside_heading:
            self._inside_heading = False
            text = "".join(self._curr_text).strip()
            self.headings.append({
                "tag": self._curr_tag,
                "text": text,
                "attrs": self._curr_attrs
            })
            self._curr_text = []
        elif tag_lower == "a" and self._inside_link:
            self._inside_link = False
            self._curr_link_data["text"] = "".join(self._curr_text).strip()
            self.links.append(self._curr_link_data)
            self._curr_link_data = {}
            self._curr_text = []
        elif tag_lower == "script" and self._inside_script:
            self._inside_script = False
            content = "".join(self._curr_text).strip()
            script_data = dict(self._curr_attrs)
            script_data["content"] = content
            self.scripts.append(script_data)
            self._curr_text = []
        elif tag_lower == "style" and self._inside_style:
            self._inside_style = False
            self.styles.append({"content": "".join(self._curr_text).strip()})
            self._curr_text = []

    def handle_data(self, data: str):
        if self._inside_title or self._inside_heading or self._inside_link or self._inside_script or self._inside_style:
            self._curr_text.append(data)
        elif not self._inside_script and not self._inside_style:
            cleaned = data.strip()
            if cleaned:
                self.text_chunks.append(cleaned)


class SEOAnalyzer:
    """
    Deterministic SEO Analyzer assessing raw HTML or project source code.
    Produces evidence-backed findings and metrics.
    """

    @classmethod
    def analyze(
        cls,
        fetch_res: FetchResult,
        target_keyword: Optional[str] = None
    ) -> Tuple[List[SEOFinding], Dict[str, Any], PerformanceSignalsData]:
        """
        Runs comprehensive deterministic checks against HTML content and fetch metadata.
        Returns:
            findings: List of SEOFinding items
            metadata: Extracted document facts (title, description, headings, word count, etc.)
            perf_signals: Measured performance signals
        """
        html = fetch_res.content or ""
        collector = DOMCollector()

        try:
            collector.feed(html)
        except Exception:
            # Fallback regex parsing if HTML is heavily malformed
            pass

        findings: List[SEOFinding] = []

        # 1. Technical SEO Checks
        cls._check_technical_seo(collector, fetch_res, findings)

        # 2. Headings Hierarchy Checks
        cls._check_headings(collector, findings)

        # 3. Image Optimization Checks
        cls._check_images(collector, findings)

        # 4. Link Health & Architecture Checks
        cls._check_links(collector, fetch_res.final_url, findings)

        # 5. Social Sharing & Metadata Checks
        cls._check_social_metadata(collector, findings)

        # 6. Structured Data & Schema.org Checks
        cls._check_structured_data(collector, findings)

        # 7. Accessibility Baseline Signals
        cls._check_accessibility(collector, findings)

        # 8. Security Signals
        cls._check_security(collector, fetch_res, findings)

        # 9. Performance & Resource Signals
        perf_data = cls._check_performance(collector, fetch_res, findings)

        # 10. Content & Target Keyword Analysis
        full_text = " ".join(collector.text_chunks)
        words = re.findall(r"\b\w+\b", full_text)
        word_count = len(words)

        cls._check_content_and_keywords(
            collector,
            full_text,
            word_count,
            target_keyword,
            findings
        )

        # Extract primary metadata
        h1_texts = [h["text"] for h in collector.headings if h["tag"] == "h1" and h["text"]]
        meta_desc = cls._get_meta_content(collector.meta_tags, "description")
        canonical_link = cls._get_link_href(collector.link_tags, "canonical")

        meta_info = {
            "html_title": collector.title_text or "",
            "meta_description": meta_desc or "",
            "canonical_url": canonical_link,
            "h1_headings": h1_texts,
            "word_count": word_count,
            "total_headings": len(collector.headings),
            "total_images": len(collector.images),
            "total_links": len(collector.links),
            "total_scripts": len(collector.scripts),
            "total_stylesheets": len([l for l in collector.link_tags if l.get("rel") == "stylesheet"]),
        }

        return findings, meta_info, perf_data

    # ─────────────────────────────────────────────────────────────────────────
    # Sub-Check Implementations
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _check_technical_seo(
        cls,
        dom: DOMCollector,
        fetch_res: FetchResult,
        findings: List[SEOFinding]
    ):
        cat = SEOCategory.TECHNICAL

        # 1. Title Tag
        title = dom.title_text
        if not title:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.CRITICAL,
                title="Missing <title> tag",
                problem="The document does not contain a <title> element.",
                evidence="No <title> tag found in HTML head.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add a descriptive, unique <title> tag (between 30 and 65 characters) summarizing the page.",
                impact="High",
                effort="Low",
                confidence=1.0,
                why_it_matters="Search engines display the title tag as the primary headline in search engine result pages (SERPs)."
            ))
        else:
            length = len(title)
            if length < 15:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.MEDIUM,
                    title="Short <title> tag",
                    problem=f"The title tag is only {length} characters long.",
                    evidence=f"Observed <title>: '{title}' ({length} chars).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Expand the title tag to 30-65 characters with relevant topic descriptors and brand name.",
                    impact="Medium",
                    effort="Low",
                    confidence=0.95,
                    why_it_matters="Very short titles miss opportunities to include descriptive keywords for users and search crawlers."
                ))
            elif length > 70:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.LOW,
                    title="Potentially long <title> tag",
                    problem=f"The title tag is {length} characters long.",
                    evidence=f"Observed <title>: '{title}' ({length} chars).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Shorten title to under 65 characters to prevent truncation in search result displays.",
                    impact="Low",
                    effort="Low",
                    confidence=0.90,
                    why_it_matters="Titles exceeding 60-70 characters are typically truncated with ellipses (...) in desktop and mobile search snippets."
                ))
            else:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.PASSED,
                    title="Title tag well-configured",
                    problem="",
                    evidence=f"Title: '{title}' ({length} characters).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Proper title length ensures optimal presentation across search result interfaces."
                ))

        # 2. Meta Description
        meta_desc = cls._get_meta_content(dom.meta_tags, "description")
        if not meta_desc:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.HIGH,
                title="Missing meta description",
                problem="The document lacks a <meta name=\"description\"> tag.",
                evidence="No meta description detected in HTML head.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add a compelling meta description tag (120-160 characters) explaining the page value proposition.",
                impact="High",
                effort="Low",
                confidence=1.0,
                why_it_matters="Meta descriptions frequently appear as search snippets and significantly influence user click-through rates (CTR)."
            ))
        else:
            length = len(meta_desc)
            if length < 50:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.MEDIUM,
                    title="Short meta description",
                    problem=f"Meta description is only {length} characters long.",
                    evidence=f"Observed: '{meta_desc[:60]}...' ({length} chars).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Expand the description to 120-160 characters with clear call-to-action and primary value points.",
                    impact="Medium",
                    effort="Low",
                    confidence=0.95,
                    why_it_matters="Short snippets provide insufficient context for potential visitors evaluating search results."
                ))
            elif length > 165:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.LOW,
                    title="Potentially long meta description",
                    problem=f"Meta description is {length} characters long.",
                    evidence=f"Observed: '{meta_desc[:60]}...' ({length} chars).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Keep description within 120-160 characters to avoid visual truncation in search snippets.",
                    impact="Low",
                    effort="Low",
                    confidence=0.90,
                    why_it_matters="Search engines cut off overly long snippets on mobile and desktop result views."
                ))
            else:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.PASSED,
                    title="Meta description present and optimal",
                    problem="",
                    evidence=f"Meta description: '{meta_desc[:70]}...' ({length} characters).",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Optimal snippet length ensures full visibility in search previews."
                ))

        # 3. Viewport Configuration
        viewport = cls._get_meta_content(dom.meta_tags, "viewport")
        if not viewport:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.CRITICAL,
                title="Missing mobile viewport configuration",
                problem="No <meta name=\"viewport\"> tag detected.",
                evidence="HTML lacks viewport declaration in head.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">.",
                impact="Critical",
                effort="Low",
                confidence=1.0,
                why_it_matters="Mobile-first indexing requires a responsive viewport configuration for proper mobile rendering."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Mobile viewport configured",
                problem="",
                evidence=f"Viewport tag: content='{viewport}'",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Ensures the page scales appropriately on mobile and tablet displays."
            ))

        # 4. Canonical Tag
        canonical = cls._get_link_href(dom.link_tags, "canonical")
        if not canonical:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="Missing canonical link",
                problem="No <link rel=\"canonical\"> tag detected.",
                evidence="HTML lacks canonical link in head.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Specify the preferred URL using <link rel=\"canonical\" href=\"https://...\">.",
                impact="Medium",
                effort="Low",
                confidence=0.95,
                why_it_matters="Canonical links prevent duplicate content penalties across URL variants (e.g. www, https, tracking params)."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Canonical link present",
                problem="",
                evidence=f"Canonical href='{canonical}'",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Clarifies authoritative page URL to search crawlers."
            ))

        # 5. Meta Robots & Indexability
        robots_meta = cls._get_meta_content(dom.meta_tags, "robots")
        if robots_meta:
            if "noindex" in robots_meta.lower():
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.HIGH,
                    title="Meta robots noindex detected",
                    problem="Page contains 'noindex' directive preventing search indexing.",
                    evidence=f"Meta robots: '{robots_meta}'",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Remove 'noindex' if this page is intended to be indexed by search engines.",
                    impact="High",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Explicit noindex directives instruct search engines to exclude the page from search results entirely."
                ))
            else:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.PASSED,
                    title="Meta robots indexing permitted",
                    problem="",
                    evidence=f"Meta robots: '{robots_meta}'",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Search engines can crawl and index the document."
                ))

        # 6. Doctype & Charset
        if not dom.doctype:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Missing HTML5 DOCTYPE declaration",
                problem="Document does not begin with <!DOCTYPE html>.",
                evidence="No DOCTYPE tag parsed.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add <!DOCTYPE html> as the first line of the document.",
                impact="Low",
                effort="Low",
                confidence=0.90,
                why_it_matters="A standard DOCTYPE declaration prevents browsers from entering quirks mode."
            ))

        # 7. Crawlability: robots.txt / sitemap.xml
        if not fetch_res.is_local:
            crawl_cat = SEOCategory.CRAWLABILITY
            if fetch_res.robots_txt:
                findings.append(SEOFinding(
                    category=crawl_cat,
                    severity=FindingSeverity.PASSED,
                    title="robots.txt detected and accessible",
                    problem="",
                    evidence="robots.txt returned HTTP 200.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Provides crawling rules and directions to search engine bots."
                ))
            else:
                findings.append(SEOFinding(
                    category=crawl_cat,
                    severity=FindingSeverity.LOW,
                    title="robots.txt unavailable or not detected",
                    problem="robots.txt was not found at the website root.",
                    evidence="HTTP request to /robots.txt failed or returned non-200.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Create a /robots.txt file specifying crawler directives and pointing to your XML sitemap.",
                    impact="Low",
                    effort="Low",
                    confidence=0.85,
                    why_it_matters="Helps manage search crawler budgets and prevent bot index overload."
                ))

            if fetch_res.sitemap_xml or (fetch_res.robots_txt and "sitemap:" in fetch_res.robots_txt.lower()):
                findings.append(SEOFinding(
                    category=crawl_cat,
                    severity=FindingSeverity.PASSED,
                    title="XML sitemap detected or referenced",
                    problem="",
                    evidence="Sitemap found at /sitemap.xml or referenced in robots.txt.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Accelerates discovery and indexing of all website URLs."
                ))
            else:
                findings.append(SEOFinding(
                    category=crawl_cat,
                    severity=FindingSeverity.MEDIUM,
                    title="Missing XML sitemap reference",
                    problem="No sitemap found at /sitemap.xml and no sitemap reference found in robots.txt.",
                    evidence="No sitemap observed at standard location.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Generate an XML sitemap (sitemap.xml) and submit it to Google Search Console and Bing Webmaster Tools.",
                    impact="Medium",
                    effort="Low",
                    confidence=0.85,
                    why_it_matters="Sitemaps guide crawlers directly to new and updated content."
                ))

    @classmethod
    def _check_headings(cls, dom: DOMCollector, findings: List[SEOFinding]):
        cat = SEOCategory.CONTENT_STRUCTURE
        headings = dom.headings
        h1s = [h for h in headings if h["tag"] == "h1"]

        # H1 Checks
        if len(h1s) == 0:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.HIGH,
                title="Missing <h1> heading",
                problem="The document has no <h1> heading element.",
                evidence="Zero <h1> tags detected in DOM.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add a single, clear <h1> heading describing the central topic of the page.",
                impact="High",
                effort="Low",
                confidence=1.0,
                why_it_matters="An H1 heading establishes the top-level semantic subject for human readers and search engines."
            ))
        elif len(h1s) > 1:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="Multiple <h1> headings detected",
                problem=f"Found {len(h1s)} separate <h1> elements on the page.",
                evidence=f"H1 tags: {[h['text'][:40] for h in h1s]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Reserve <h1> for the primary page title and use <h2>-<h6> for sectional hierarchy.",
                impact="Medium",
                effort="Low",
                confidence=0.90,
                why_it_matters="While HTML5 permits multiple H1s in nested sectioning roots, a single primary H1 provides clearer structural hierarchy."
            ))
        else:
            h1_text = h1s[0]["text"]
            if not h1_text:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.HIGH,
                    title="Empty <h1> heading",
                    problem="The <h1> tag exists but contains no visible text.",
                    evidence="<h1></h1> tag has empty content.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Add meaningful descriptive text inside the <h1> tag.",
                    impact="High",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Empty headings create accessibility voids and fail to convey page intent."
                ))
            else:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.PASSED,
                    title="Single valid <h1> heading detected",
                    problem="",
                    evidence=f"<h1>: '{h1_text[:60]}'",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Provides clear top-level topic outline."
                ))

        # Check for empty sub-headings and skipped hierarchy
        empty_headings = [h for h in headings if not h["text"] and h["tag"] != "h1"]
        if empty_headings:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title=f"Empty sub-headings detected ({len(empty_headings)})",
                problem=f"Found {len(empty_headings)} heading tags containing no meaningful text.",
                evidence=f"Empty tags: {[h['tag'] for h in empty_headings[:5]]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Remove empty heading tags or provide descriptive section titles.",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Empty heading elements disrupt assistive technology screen readers and clean document semantics."
            ))

        # Check for skipped heading levels (e.g. H1 directly to H4)
        skipped_levels = []
        last_level = 0
        for h in headings:
            level = int(h["tag"][1])
            if last_level > 0 and level > last_level + 1:
                skipped_levels.append(f"H{last_level} -> H{level}")
            last_level = level

        if skipped_levels:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Skipped heading levels detected",
                problem=f"Document hierarchy skips levels: {', '.join(skipped_levels[:3])}.",
                evidence=f"Skipped transitions: {skipped_levels}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Maintain sequential heading hierarchy (H1 -> H2 -> H3) without skipping levels.",
                impact="Low",
                effort="Low",
                confidence=0.85,
                why_it_matters="Sequential heading levels create an intuitive outline for screen readers and search indexers."
            ))

    @classmethod
    def _check_images(cls, dom: DOMCollector, findings: List[SEOFinding]):
        cat = SEOCategory.ON_PAGE
        images = dom.images

        if not images:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="No images on page or all assets accounted for",
                problem="",
                evidence="0 images detected in document.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Image audits apply when images are embedded in the markup."
            ))
            return

        missing_alt = []
        generic_alt = []
        missing_dimensions = []
        non_lazy = 0

        for img in images:
            alt = img.get("alt")
            role = img.get("role", "").lower()
            aria_hidden = img.get("aria-hidden", "").lower()
            is_decorative = role == "presentation" or role == "none" or aria_hidden == "true"

            if alt is None:
                missing_alt.append(img.get("src", "unknown"))
            elif alt == "" and not is_decorative:
                # Empty alt without decorative role may be an untagged image
                pass
            elif alt and alt.strip().lower() in ("image", "photo", "picture", "icon", "untitled", "img", "graphic"):
                generic_alt.append(f"src='{img.get('src', '')}' alt='{alt}'")

            # Check explicit dimensions
            if not img.get("width") or not img.get("height"):
                missing_dimensions.append(img.get("src", "unknown"))

            if img.get("loading", "").lower() != "lazy":
                non_lazy += 1

        if missing_alt:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.HIGH,
                title=f"Images missing alt attribute ({len(missing_alt)})",
                problem=f"{len(missing_alt)} out of {len(images)} images have no alt attribute.",
                evidence=f"Missing alt on images: {missing_alt[:4]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add descriptive alt text to all informational images (use alt=\"\" with role=\"presentation\" only for decorative icons).",
                impact="High",
                effort="Low",
                confidence=1.0,
                why_it_matters="Alt text is critical for accessibility screen readers and allows search engines to index images in visual search."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="All images contain alt attributes",
                problem="",
                evidence=f"All {len(images)} images have alt declarations.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Ensures image accessibility and image search indexing."
            ))

        if generic_alt:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title=f"Generic image alt text detected ({len(generic_alt)})",
                problem=f"Some images use non-descriptive alt values like 'image' or 'photo'.",
                evidence=f"Examples: {generic_alt[:3]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Replace generic placeholder alt tags with specific descriptions of the image content.",
                impact="Low",
                effort="Low",
                confidence=0.90,
                why_it_matters="Descriptive alt text provides meaningful context to visually impaired users and image search crawlers."
            ))

        if missing_dimensions and len(images) > 2:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Images without explicit width/height dimensions",
                problem=f"{len(missing_dimensions)} images lack explicit width and height HTML attributes.",
                evidence=f"Examples: {missing_dimensions[:3]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Specify width and height attributes on <img> tags to reserve layout space and prevent Cumulative Layout Shift (CLS).",
                impact="Low",
                effort="Medium",
                confidence=0.85,
                why_it_matters="Explicit image dimensions allow the browser to allocate aspect-ratio boxes before images finish downloading."
            ))

    @classmethod
    def _check_links(
        cls,
        dom: DOMCollector,
        base_url: str,
        findings: List[SEOFinding]
    ):
        cat = SEOCategory.ON_PAGE
        links = dom.links

        if not links:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Low internal/external link count",
                problem="The document contains zero hyperlink elements.",
                evidence="0 <a> tags detected.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add internal navigation links and relevant external resource references.",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Links form the connective crawl graph for search engines and facilitate user navigation."
            ))
            return

        empty_anchors = []
        generic_anchors = []
        insecure_external_targets = []
        internal_count = 0
        external_count = 0

        parsed_base = urllib.parse.urlparse(base_url) if base_url else None
        base_host = parsed_base.netloc.lower() if parsed_base else ""

        for link in links:
            href = link.get("href", "").strip()
            text = link.get("text", "").strip()
            aria_label = link.get("aria-label", "").strip()
            title_attr = link.get("title", "").strip()
            target = link.get("target", "").lower()
            rel = link.get("rel", "").lower()

            effective_label = text or aria_label or title_attr

            # Check empty anchor text
            if not effective_label and not href.startswith("#") and not href.startswith("javascript:"):
                empty_anchors.append(href)

            # Check generic anchor text
            if effective_label.lower() in ("click here", "read more", "learn more", "link", "here", "more"):
                generic_anchors.append(f"href='{href}' text='{effective_label}'")

            # Check internal vs external
            if href.startswith("http://") or href.startswith("https://"):
                parsed_href = urllib.parse.urlparse(href)
                if parsed_href.netloc.lower() == base_host or not base_host:
                    internal_count += 1
                else:
                    external_count += 1
                    # External target blank security check
                    if target == "_blank" and ("noopener" not in rel and "noreferrer" not in rel):
                        insecure_external_targets.append(href)
            elif href and not href.startswith("#") and not href.startswith("javascript:"):
                internal_count += 1

        if empty_anchors:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title=f"Links with empty anchor text ({len(empty_anchors)})",
                problem=f"{len(empty_anchors)} links contain no descriptive text or aria-label.",
                evidence=f"Empty anchor hrefs: {empty_anchors[:4]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Provide meaningful descriptive text or aria-label for all hyperlinks.",
                impact="Medium",
                effort="Low",
                confidence=0.95,
                why_it_matters="Search engines use anchor text as a relevance signal for the destination page."
            ))

        if generic_anchors:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title=f"Generic link anchor text detected ({len(generic_anchors)})",
                problem="Links use generic anchor phrases like 'click here' or 'read more'.",
                evidence=f"Examples: {generic_anchors[:3]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Use keyword-rich descriptive anchor text indicating the destination topic.",
                impact="Low",
                effort="Low",
                confidence=0.90,
                why_it_matters="Descriptive anchors provide semantic context to search engines about target page subjects."
            ))

        if insecure_external_targets:
            findings.append(SEOFinding(
                category=SEOCategory.TECHNICAL,
                severity=FindingSeverity.LOW,
                title="External target='_blank' links missing rel='noopener'",
                problem=f"{len(insecure_external_targets)} external links open in a new tab without rel='noopener noreferrer'.",
                evidence=f"Examples: {insecure_external_targets[:3]}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add rel=\"noopener noreferrer\" to all external target=\"_blank\" hyperlinks.",
                impact="Low",
                effort="Low",
                confidence=0.95,
                why_it_matters="Prevents window.opener reverse-tabnabbing security vulnerabilities."
            ))

        findings.append(SEOFinding(
            category=cat,
            severity=FindingSeverity.PASSED,
            title="Link architecture evaluated",
            problem="",
            evidence=f"Detected {internal_count} internal links and {external_count} external links ({len(links)} total).",
            evidence_type=EvidenceType.OBSERVED,
            recommendation="",
            impact="Low",
            effort="Low",
            confidence=1.0,
            why_it_matters="Healthy ratio of internal and external references supports crawl discovery."
        ))

    @classmethod
    def _check_social_metadata(cls, dom: DOMCollector, findings: List[SEOFinding]):
        cat = SEOCategory.SOCIAL_METADATA

        # OpenGraph
        og_title = cls._get_meta_property(dom.meta_tags, "og:title")
        og_desc = cls._get_meta_property(dom.meta_tags, "og:description")
        og_image = cls._get_meta_property(dom.meta_tags, "og:image")
        og_url = cls._get_meta_property(dom.meta_tags, "og:url")
        og_type = cls._get_meta_property(dom.meta_tags, "og:type")

        missing_og = []
        if not og_title: missing_og.append("og:title")
        if not og_desc: missing_og.append("og:description")
        if not og_image: missing_og.append("og:image")

        if missing_og:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title=f"Incomplete Open Graph social metadata (missing {len(missing_og)})",
                problem=f"Missing core Open Graph tags: {', '.join(missing_og)}.",
                evidence=f"Missing properties: {missing_og}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add og:title, og:description, and og:image tags for rich social card previews.",
                impact="Medium",
                effort="Low",
                confidence=1.0,
                why_it_matters="Open Graph tags control how links appear when shared on LinkedIn, Facebook, Slack, and Discord."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Complete Open Graph social tags detected",
                problem="",
                evidence=f"og:title='{og_title[:40]}', og:image detected.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Ensures high-fidelity rich media previews during social sharing."
            ))

        # Twitter Cards
        twitter_card = cls._get_meta_name_or_property(dom.meta_tags, "twitter:card")
        if not twitter_card:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Missing Twitter / X Card metadata",
                problem="No <meta name=\"twitter:card\"> declaration detected.",
                evidence="HTML lacks twitter:card tag.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add <meta name=\"twitter:card\" content=\"summary_large_image\">.",
                impact="Low",
                effort="Low",
                confidence=0.90,
                why_it_matters="Controls snippet layout and card size when content is shared on Twitter/X."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Twitter / X Card metadata configured",
                problem="",
                evidence=f"twitter:card='{twitter_card}'",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Generates large image preview cards on Twitter/X."
            ))

    @classmethod
    def _check_structured_data(cls, dom: DOMCollector, findings: List[SEOFinding]):
        cat = SEOCategory.STRUCTURED_DATA
        ld_json_scripts = [s for s in dom.scripts if s.get("type") == "application/ld+json"]

        if not ld_json_scripts:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="No JSON-LD structured data detected",
                problem="Page does not declare Schema.org structured data in JSON-LD format.",
                evidence="0 <script type=\"application/ld+json\"> blocks observed.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add JSON-LD markup declaring appropriate Schema types (e.g. WebSite, Organization, Article, Product).",
                impact="Medium",
                effort="Medium",
                confidence=0.95,
                why_it_matters="Structured data helps search engines understand entity relationships and qualifies pages for SERP Rich Snippets."
            ))
            return

        valid_schemas = []
        for s in ld_json_scripts:
            content = s.get("content", "").strip()
            if not content:
                continue
            try:
                parsed = json.loads(content)
                schema_type = parsed.get("@type", "Unknown") if isinstance(parsed, dict) else "Array/Graph"
                valid_schemas.append(schema_type)
            except json.JSONDecodeError as e:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.HIGH,
                    title="Malformed JSON-LD structured data syntax",
                    problem=f"JSON-LD script block has syntax error: {str(e)}",
                    evidence=f"JSON parse error at line {e.lineno}, col {e.colno}: {content[:80]}...",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Fix JSON syntax errors (check for trailing commas, unescaped quotes, or comments).",
                    impact="High",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Malformed JSON-LD cannot be parsed by Google and invalidates all structured data on the page."
                ))

        if valid_schemas:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Valid Schema.org JSON-LD structured data detected",
                problem="",
                evidence=f"Parsed {len(valid_schemas)} schema blocks: {valid_schemas}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Enables search engines to generate enhanced rich results (breadcrumbs, ratings, application previews)."
            ))

    @classmethod
    def _check_accessibility(cls, dom: DOMCollector, findings: List[SEOFinding]):
        cat = SEOCategory.ACCESSIBILITY_SIGNALS

        # 1. HTML lang attribute
        lang = dom.html_attrs.get("lang")
        if not lang:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="Missing lang attribute on <html> element",
                problem="The root <html> tag lacks a language declaration attribute (e.g. lang=\"en\").",
                evidence="<html> tag has no lang attribute.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Add lang=\"en\" (or appropriate language code) to the <html> tag.",
                impact="Medium",
                effort="Low",
                confidence=1.0,
                why_it_matters="Screen readers and international search indexers rely on the lang attribute for correct pronunciation and geographic targeting."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="HTML document language declared",
                problem="",
                evidence=f"<html lang='{lang}'>",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Supports multilingual indexing and accessible screen-reader translation."
            ))

        # 2. Semantic Structure Elements
        semantics = dom.semantic_tags
        if len(semantics) < 2:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title="Low usage of semantic HTML5 landmarks",
                problem=f"Found only {len(semantics)} semantic tags ({list(semantics)}).",
                evidence=f"Observed semantic tags: {list(semantics)}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Use semantic elements (<main>, <nav>, <header>, <footer>, <article>) instead of generic <div> containers.",
                impact="Low",
                effort="Medium",
                confidence=0.85,
                why_it_matters="Semantic landmarks clarify document navigation landmarks for assistive technologies and search bots."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Semantic HTML5 landmarks detected",
                problem="",
                evidence=f"Semantic tags present: {list(semantics)}",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Provides structured accessibility landmarks throughout the page."
            ))

    @classmethod
    def _check_security(
        cls,
        dom: DOMCollector,
        fetch_res: FetchResult,
        findings: List[SEOFinding]
    ):
        cat = SEOCategory.TECHNICAL

        # HTTPS enforcement
        if fetch_res.final_url.startswith("http://"):
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.HIGH,
                title="Insecure HTTP protocol in use",
                problem="The website is served over unencrypted HTTP rather than HTTPS.",
                evidence=f"Final URL: '{fetch_res.final_url}'",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Install an SSL/TLS certificate and configure 301 redirects from HTTP to HTTPS.",
                impact="High",
                effort="Medium",
                confidence=1.0,
                why_it_matters="HTTPS is an explicit Google search ranking factor and essential for visitor data security and browser trust."
            ))
        elif fetch_res.final_url.startswith("https://"):
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Secure HTTPS protocol active",
                problem="",
                evidence=f"HTTPS active on '{fetch_res.final_url}'",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Ensures encrypted communication and satisfies search engine security criteria."
            ))

        # Mixed content detection
        if fetch_res.final_url.startswith("https://"):
            insecure_assets = []
            for img in dom.images:
                src = img.get("src", "")
                if src.startswith("http://"):
                    insecure_assets.append(f"Image: {src}")
            for s in dom.scripts:
                src = s.get("src", "")
                if src.startswith("http://"):
                    insecure_assets.append(f"Script: {src}")

            if insecure_assets:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.HIGH,
                    title=f"Mixed active/passive content detected ({len(insecure_assets)})",
                    problem="Secure HTTPS page requests unencrypted HTTP external subresources.",
                    evidence=f"Insecure resources: {insecure_assets[:3]}",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Update all asset URLs to use HTTPS or relative protocol URLs.",
                    impact="High",
                    effort="Low",
                    confidence=0.95,
                    why_it_matters="Modern browsers block mixed active content and trigger security warning icons in address bars."
                ))

    @classmethod
    def _check_performance(
        cls,
        dom: DOMCollector,
        fetch_res: FetchResult,
        findings: List[SEOFinding]
    ) -> PerformanceSignalsData:
        cat = SEOCategory.PERFORMANCE_SIGNALS
        doc_size = fetch_res.content_length
        latency_ms = fetch_res.latency_ms

        script_count = len(dom.scripts)
        stylesheet_count = len([l for l in dom.link_tags if l.get("rel") == "stylesheet"]) + len(dom.styles)
        image_count = len(dom.images)
        total_resources = script_count + stylesheet_count + image_count

        perf_data = PerformanceSignalsData(
            response_time_ms=latency_ms,
            document_size_bytes=doc_size,
            script_count=script_count,
            stylesheet_count=stylesheet_count,
            image_count=image_count,
            total_resources=total_resources,
            is_measured=True
        )

        # 1. Document size check
        doc_size_kb = doc_size / 1024
        if doc_size_kb > 300:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="Large HTML document payload",
                problem=f"HTML document payload is {doc_size_kb:.1f} KB (exceeds 300 KB guideline).",
                evidence=f"Raw document size: {doc_size} bytes ({doc_size_kb:.1f} KB).",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Minify HTML markup, eliminate bloated inline scripts/SVGs, and enable Gzip/Brotli compression.",
                impact="Medium",
                effort="Medium",
                confidence=0.95,
                why_it_matters="Heavy initial HTML payloads delay DOM parsing and Time to First Byte (TTFB)."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="HTML document size is optimal",
                problem="",
                evidence=f"Document payload: {doc_size_kb:.1f} KB.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Enables rapid initial packet delivery."
            ))

        # 2. Latency check (if measured from live URL)
        if not fetch_res.is_local and latency_ms > 0:
            if latency_ms > 1500:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.HIGH,
                    title="Slow server response latency",
                    problem=f"Server response time was {latency_ms:.0f} ms (exceeds 1.5s threshold).",
                    evidence=f"Measured HTTP roundtrip latency: {latency_ms:.1f} ms.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="Implement edge CDN caching, optimize database queries, and upgrade server hosting resources.",
                    impact="High",
                    effort="High",
                    confidence=0.90,
                    why_it_matters="Fast server response is a critical foundation for Core Web Vitals (LCP and TTFB)."
                ))
            elif latency_ms < 600:
                findings.append(SEOFinding(
                    category=cat,
                    severity=FindingSeverity.PASSED,
                    title="Fast initial server response",
                    problem="",
                    evidence=f"Measured latency: {latency_ms:.1f} ms.",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Satisfies Google guidelines for sub-600ms Time to First Byte."
                ))

        # 3. Excessive scripts check
        if script_count > 25:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.LOW,
                title=f"High script tag count ({script_count} scripts)",
                problem=f"Page includes {script_count} individual script tags which may block parsing.",
                evidence=f"{script_count} script declarations detected.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Bundle and defer JavaScript scripts with defer or async attributes.",
                impact="Low",
                effort="Medium",
                confidence=0.85,
                why_it_matters="Unoptimized synchronous scripts block the main thread and degrade interaction metrics."
            ))

        return perf_data

    @classmethod
    def _check_content_and_keywords(
        cls,
        dom: DOMCollector,
        full_text: str,
        word_count: int,
        target_keyword: Optional[str],
        findings: List[SEOFinding]
    ):
        cat = SEOCategory.CONTENT_STRUCTURE

        # 1. Thin Content Check
        if word_count < 100:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.MEDIUM,
                title="Thin on-page text content",
                problem=f"Document contains only {word_count} words of visible text.",
                evidence=f"Extracted visible word count: {word_count}.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="Expand comprehensive on-page textual content to thoroughly address the user search intent.",
                impact="Medium",
                effort="Medium",
                confidence=0.90,
                why_it_matters="Thin pages struggle to rank for competitive search queries due to insufficient semantic depth."
            ))
        else:
            findings.append(SEOFinding(
                category=cat,
                severity=FindingSeverity.PASSED,
                title="Adequate textual content volume",
                problem="",
                evidence=f"Word count: {word_count} words.",
                evidence_type=EvidenceType.OBSERVED,
                recommendation="",
                impact="Low",
                effort="Low",
                confidence=1.0,
                why_it_matters="Provides substantive context for topic topical authority."
            ))

        # 2. Target Keyword Analysis (if user supplied)
        if target_keyword and target_keyword.strip():
            kw = target_keyword.strip().lower()
            title_lower = (dom.title_text or "").lower()
            meta_desc_lower = (cls._get_meta_content(dom.meta_tags, "description") or "").lower()
            h1_lower = " ".join([h["text"].lower() for h in dom.headings if h["tag"] == "h1"])
            body_lower = full_text.lower()

            kw_in_title = kw in title_lower
            kw_in_desc = kw in meta_desc_lower
            kw_in_h1 = kw in h1_lower

            kw_matches = len(re.findall(r"\b" + re.escape(kw) + r"\b", body_lower))
            density_percent = (kw_matches / max(1, word_count)) * 100

            if not kw_in_title:
                findings.append(SEOFinding(
                    category=SEOCategory.ON_PAGE,
                    severity=FindingSeverity.MEDIUM,
                    title=f"Target keyword missing from <title> ('{kw}')",
                    problem=f"Target keyword '{kw}' was not found in the page title tag.",
                    evidence=f"<title>: '{dom.title_text}'",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation=f"Naturally incorporate '{kw}' near the beginning of the title tag.",
                    impact="Medium",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Title keyword prominence is one of the strongest on-page topical signals."
                ))
            else:
                findings.append(SEOFinding(
                    category=SEOCategory.ON_PAGE,
                    severity=FindingSeverity.PASSED,
                    title=f"Target keyword present in <title> ('{kw}')",
                    problem="",
                    evidence=f"Keyword '{kw}' found in title: '{dom.title_text}'",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation="",
                    impact="Low",
                    effort="Low",
                    confidence=1.0,
                    why_it_matters="Aligns title with search query target."
                ))

            if not kw_in_h1:
                findings.append(SEOFinding(
                    category=SEOCategory.ON_PAGE,
                    severity=FindingSeverity.LOW,
                    title=f"Target keyword missing from <h1> heading",
                    problem=f"Target keyword '{kw}' was not found in any <h1> heading.",
                    evidence=f"H1 headings: {[h['text'] for h in dom.headings if h['tag'] == 'h1']}",
                    evidence_type=EvidenceType.OBSERVED,
                    recommendation=f"Include '{kw}' in the primary <h1> heading to reinforce page theme.",
                    impact="Low",
                    effort="Low",
                    confidence=0.95,
                    why_it_matters="H1 keyword presence confirms relevance to the visitor immediately upon landing."
                ))

            if density_percent > 3.5:
                findings.append(SEOFinding(
                    category=SEOCategory.ON_PAGE,
                    severity=FindingSeverity.HIGH,
                    title="Potential keyword stuffing detected",
                    problem=f"Target keyword density is {density_percent:.1f}% ({kw_matches} occurrences in {word_count} words).",
                    evidence=f"Keyword count: {kw_matches} | Density: {density_percent:.1f}%",
                    evidence_type=EvidenceType.INFERRED,
                    recommendation="Reduce repetitive keyword instances. Use natural synonyms and related semantic concepts.",
                    impact="High",
                    effort="Medium",
                    confidence=0.85,
                    why_it_matters="Search engines penalize unnatural keyword repetition and prioritize natural conversational prose."
                ))

    # ─────────────────────────────────────────────────────────────────────────
    # Helper extractors
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_meta_content(meta_tags: List[Dict[str, str]], name_or_prop: str) -> Optional[str]:
        target = name_or_prop.lower()
        for m in meta_tags:
            name = m.get("name", "").lower()
            prop = m.get("property", "").lower()
            if name == target or prop == target:
                return m.get("content", "").strip()
        return None

    @staticmethod
    def _get_meta_property(meta_tags: List[Dict[str, str]], prop_name: str) -> Optional[str]:
        target = prop_name.lower()
        for m in meta_tags:
            if m.get("property", "").lower() == target:
                return m.get("content", "").strip()
        return None

    @staticmethod
    def _get_meta_name_or_property(meta_tags: List[Dict[str, str]], name: str) -> Optional[str]:
        target = name.lower()
        for m in meta_tags:
            if m.get("name", "").lower() == target or m.get("property", "").lower() == target:
                return m.get("content", "").strip()
        return None

    @staticmethod
    def _get_link_href(link_tags: List[Dict[str, str]], rel_val: str) -> Optional[str]:
        target = rel_val.lower()
        for l in link_tags:
            if l.get("rel", "").lower() == target:
                return l.get("href", "").strip()
        return None
