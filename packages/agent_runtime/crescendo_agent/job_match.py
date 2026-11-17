"""Rank job postings against a resume by keywords (JOB-F02). Local and deterministic.

Score (0-100) = 30% title match + 70% skill coverage:

- title match: share of the search's words (e.g. "applied ai engineer") found in
  the posting title, with a few synonyms (ai ~ ml/llm, engineer ~ developer).
  Postings below ``min_title_match`` are not relevant to the search and are dropped.
- skill coverage: of the skills the posting mentions, the share also on the
  resume, as matched / (job skills + SMOOTHING) so a posting naming few skills
  can't score high on thin evidence. Skills come from one explicit vocabulary
  (SKILLS) plus what resume skills imply (IMPLIES), so every score can be
  explained as matched and missing keywords.

Keyword matching cannot judge depth of experience or read between the lines; it
is a transparent first filter, not a hiring decision. No text leaves the machine.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re

from .job_sources import Posting, normalize_country

TITLE_WEIGHT, SKILL_WEIGHT = 0.3, 0.7

# canonical skill -> regex (case-insensitive unless the pattern sets (?-i:...)).
SKILLS = {
    # Languages
    "Python": r"\bpython\b", "TypeScript": r"\btypescript\b", "JavaScript": r"\bjavascript\b",
    "Java": r"\bjava\b(?!\s*script)", "Go": r"\bgolang\b|(?-i:\bGo\b)(?=\s*[,/)]|\s+and\b|\s+or\b)",
    "Rust": r"\brust\b", "C++": r"\bc\+\+", "C#": r"\bc#", "Scala": r"\bscala\b", "Kotlin": r"\bkotlin\b",
    "Swift": r"(?-i:\bSwift\b)", "Ruby": r"\bruby\b", "SQL": r"\bsql\b",
    # Web and APIs
    "React": r"\breact(?:\.js|js)?\b", "Next.js": r"\bnext\.?js\b", "Node.js": r"\bnode(?:\.js|js)\b",
    "FastAPI": r"\bfastapi\b", "Django": r"\bdjango\b", "Flask": r"\bflask\b", "GraphQL": r"\bgraphql\b",
    "REST APIs": r"\brest(?:ful)?\s+apis?\b", "gRPC": r"\bgrpc\b",
    # Data
    "PostgreSQL": r"\bpostgres(?:ql)?\b", "MySQL": r"\bmysql\b", "MongoDB": r"\bmongo(?:db)?\b",
    "Redis": r"\bredis\b", "Elasticsearch": r"\belastic\s*search\b", "Snowflake": r"\bsnowflake\b",
    "BigQuery": r"\bbig\s*query\b", "Spark": r"\b(?:py)?spark\b", "Airflow": r"\bairflow\b",
    "Kafka": r"\bkafka\b", "dbt": r"\bdbt\b", "Pandas": r"\bpandas\b", "NumPy": r"\bnumpy\b",
    "Data pipelines": r"\bdata\s+pipelines?\b|\betl\b",
    # Cloud and infrastructure
    "AWS": r"\baws\b|\bamazon\s+web\s+services\b", "GCP": r"\bgcp\b|\bgoogle\s+cloud\b",
    "Azure": r"\bazure\b", "Docker": r"\bdocker\b|\bcontainers?\b", "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "Terraform": r"\bterraform\b", "CI/CD": r"\bci\s*/\s*cd\b", "Linux": r"\blinux\b",
    "Distributed systems": r"\bdistributed\s+systems?\b", "Microservices": r"\bmicro-?services?\b",
    # Machine learning
    "Machine learning": r"\bmachine\s+learning\b", "Deep learning": r"\bdeep\s+learning\b",
    "PyTorch": r"\bpytorch\b", "TensorFlow": r"\btensorflow\b", "JAX": r"(?-i:\bJAX\b)",
    "scikit-learn": r"\bscikit-?learn\b|\bsklearn\b", "NLP": r"\bnlp\b|\bnatural\s+language\s+processing\b",
    "Computer vision": r"\bcomputer\s+vision\b", "Reinforcement learning": r"\breinforcement\s+learning\b|\brlhf\b",
    "MLOps": r"\bmlops\b", "Model serving": r"\bmodel\s+(?:serving|deployment|inference)\b|\binference\b",
    "GPU/CUDA": r"\bcuda\b|\bgpus?\b", "Statistics": r"\bstatistic(?:s|al)\b",
    # LLMs and applied AI
    "LLMs": r"\bllms?\b|\blarge\s+language\s+models?\b", "Generative AI": r"\bgen(?:erative)?\s*ai\b",
    "Prompt engineering": r"\bprompt(?:ing|\s+engineering|s)\b", "RAG": r"\brag\b|\bretrieval[-\s]augmented\b",
    "Embeddings": r"\bembeddings?\b", "Vector databases": r"\bvector\s+(?:databases?|dbs?|stores?|search)\b"
    r"|\bpinecone\b|\bweaviate\b|\bpgvector\b|\bfaiss\b|\bchroma(?:db)?\b",
    "Fine-tuning": r"\bfine-?tun(?:e|ed|ing)\b", "Evals": r"\bevals?\b|\bevaluation\s+(?:frameworks?|harness)",
    "AI agents": r"\b(?:ai|llm|autonomous|coding)\s+agents?\b|\bagentic\b|\bmulti-?agent\b", "Tool use": r"\btool\s+(?:use|calling)\b|\bfunction\s+calling\b",
    "LangChain": r"\blangchain\b|\blanggraph\b", "LlamaIndex": r"\bllama\s*index\b",
    "Hugging Face": r"\bhugging\s*face\b", "Transformers": r"\btransformers?\b(?!\s+(?:electrical|power))",
    "OpenAI API": r"\bopenai\b", "Claude/Anthropic API": r"\bclaude\b|\banthropic\b", "vLLM": r"\bvllm\b",
    "Amazon Bedrock": r"\b(?:amazon\s+|aws\s+)?bedrock\b",
    # Architecture and operations (added after the first real-resume run, November 17, 2026)
    "Temporal": r"\btemporal\.io\b|\btemporal\s+(?:workflows?|cloud|sdk|server)\b|(?-i:\bTemporal\b)(?=\s*[,/)])"
                r"|\bdurable\s+(?:execution|workflows?)\b",
    "Event-driven architecture": r"\bevent[-\s]driven\b",
    "Observability": r"\bobservability\b|\bopentelemetry\b|\bdatadog\b|\bprometheus\b|\bgrafana\b",
    "Supabase": r"\bsupabase\b",
    "Database design": r"\b(?:database|schema|data)\s+(?:design|modell?ing)\b",
    "Application security": r"\bappsec\b|\bapplication\s+security\b|\bowasp\b|\bsast\b|\bdast\b|\bsemgrep\b"
                            r"|\bsecure\s+coding\b|\bthreat\s+model(?:ing|ling)?\b",
    "React Native": r"\breact\s+native\b", "iOS": r"(?-i:\biOS\b)|\bswiftui\b",
    "Payments integration": r"\bstripe\s+(?:api|connect|integration)\b|\bpayments?\s+(?:integrations?|processing)\b",
    "Workflow automation": r"\bworkflow\s+automation\b|\bpower\s+automate\b|\bzapier\b|\bn8n\b",
    "Japanese": r"(?-i:\bJapanese\b)",
    # Practice
    "A/B testing": r"\ba\s*/\s*b\s+test", "System design": r"\bsystem\s+design\b",
}
_SKILL_PATTERNS = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in SKILLS.items()}

# Skills a resume demonstrates without naming them (first live run, November 17, 2026: a
# RAG + OpenAI resume showed "LLMs" as a gap). Applied to the resume side only.
_LLM_WORK = {"RAG", "Prompt engineering", "Fine-tuning", "OpenAI API", "Claude/Anthropic API",
             "LangChain", "LlamaIndex", "Evals", "AI agents", "Tool use", "vLLM"}
IMPLIES = {**{skill: {"LLMs", "Generative AI"} for skill in _LLM_WORK},
           "PyTorch": {"Deep learning", "Machine learning"}, "TensorFlow": {"Deep learning", "Machine learning"},
           "JAX": {"Deep learning", "Machine learning"}, "scikit-learn": {"Machine learning"},
           "Deep learning": {"Machine learning"}, "Hugging Face": {"Transformers"},
           "Kubernetes": {"Docker"}, "Next.js": {"React"}, "TypeScript": {"JavaScript"},
           "Amazon Bedrock": {"LLMs", "Generative AI", "AWS"}, "Temporal": {"Distributed systems"},
           "Supabase": {"PostgreSQL"}, "React Native": {"React"}}
# Coverage = matched / (job skills + SMOOTHING): a posting naming 5 skills cannot score
# as strongly as one naming 13 from the same match rate (thin evidence).
SMOOTHING = 2

STOPWORDS = {"a", "an", "the", "of", "for", "and", "or", "in", "at", "to", "with", "role", "job", "position"}
SYNONYMS = {
    "ai": {"ai", "ml", "llm", "genai", "artificial", "intelligence", "machine", "learning"},
    "ml": {"ml", "ai", "machine", "learning"},
    "engineer": {"engineer", "engineering", "developer", "swe"},
    "developer": {"developer", "engineer", "engineering"},
    "software": {"software", "swe"},
    "scientist": {"scientist", "science"},
    "manager": {"manager", "management", "lead"},
    "frontend": {"frontend", "front", "ui"},
    "backend": {"backend", "back", "server"},
    "fullstack": {"fullstack", "full", "stack"},
}
# "N+ years ... experience" within one sentence ("Founded 10 years ago. Great experience" is not).
EXPERIENCE = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*|to\s+\d{1,2}\s*)?(?:years?|yrs?)\b"
                        r"[^.!?;\n]{0,40}?\bexperience", re.IGNORECASE)


def extract_skills(text: str) -> set[str]:
    """Canonical skills from SKILLS mentioned anywhere in text."""
    return {name for name, pattern in _SKILL_PATTERNS.items() if pattern.search(text or "")}


def resume_skills(text: str) -> set[str]:
    """Skills named on the resume plus those they imply (IMPLIES), one level deep."""
    named = extract_skills(text)
    return named | {implied for skill in named for implied in IMPLIES.get(skill, ())}


def company_label(posting: Posting) -> str:
    """The ATS company name, or a readable form of the board slug ('charge-robotics' -> 'Charge Robotics')."""
    return posting.company_name or " ".join(part.capitalize() for part in re.split(r"[-_.]+", posting.company) if part)


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9+#]+", (text or "").lower()) if w not in STOPWORDS]


def title_match(query: str, title: str) -> float:
    """Share of the query's words present in the title (with SYNONYMS). 0 when the query is empty."""
    wanted, have = words(query), set(words(title))
    if not wanted:
        return 0.0
    hits = sum(1 for w in wanted if SYNONYMS.get(w, {w}) & have)
    return hits / len(wanted)


def years_asked(text: str) -> int | None:
    """Smallest 'N+ years ... experience' requirement stated, if any (N <= 20)."""
    found = [int(m.group(1)) for m in EXPERIENCE.finditer(text or "") if 0 < int(m.group(1)) <= 20]
    return min(found) if found else None


@dataclass(frozen=True)
class Match:
    score: int
    title_match: float
    skill_coverage: float
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    years_asked: int | None
    posting: Posting = field(compare=False)
    other_postings: int = 0  # same role posted for other locations (see group_duplicates)

    def as_dict(self) -> dict:
        p = self.posting
        return {"score": self.score, "title": p.title, "company": company_label(p),
                "url": p.url, "source": p.source, "locations": list(p.locations),
                "countries": sorted(posting_countries(p)), "workplace": p.workplace,
                "compensation": p.compensation, "posted": p.published_at, "department": p.department,
                "title_match": round(self.title_match, 2), "skill_coverage": round(self.skill_coverage, 2),
                "matched_skills": list(self.matched_skills), "missing_skills": list(self.missing_skills),
                "years_asked": self.years_asked, "other_postings": self.other_postings}


SENIOR_TITLE = re.compile(r"\b(?:senior|sr\.?|staff|lead|principal|head|director|manager|vp)\b", re.IGNORECASE)


def is_senior_title(title: str) -> bool:
    """True for titles above early-career level (Senior, Staff, Lead, Manager, ...)."""
    return bool(SENIOR_TITLE.search(title or ""))


# Places named in free-text locations -> country or region (JOB-F06). Used with Ashby's
# structured countries and alone for Greenhouse/Lever, which give only text. A live
# Ashby sample passed "Toronto", "London", and "Europe; Israel (remote)" through a
# text-only "remote" filter; these names let a country filter drop them.
_US_STATES = ("AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|"
              "NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC")
PLACE_PATTERNS = {
    "United States": r"\bunited\s+states\b|\busa\b|\bu\.s\.(?:a\.)?|(?-i:\bUS\b)|(?-i:,\s*(?:" + _US_STATES + r")\b)"
                     r"|\bnyc\b|\bnew\s+york\b|\bsan\s+francisco\b|\bseattle\b|\bboston\b|\baustin\b"
                     r"|\bchicago\b|\blos\s+angeles\b|\bdenver\b|\bmiami\b|\batlanta\b|\bwashington,?\s+d\.?c\b",
    "United Kingdom": r"\bunited\s+kingdom\b|\buk\b|\bengland\b|\blondon\b|\bscotland\b|\bmanchester\b",
    "Canada": r"\bcanada\b|\btoronto\b|\bvancouver\b|\bmontr[eé]al\b|\bontario\b",
    "Germany": r"\bgermany\b|\bberlin\b|\bmunich\b", "France": r"\bfrance\b|\bparis\b",
    "Netherlands": r"\bnetherlands\b|\bamsterdam\b", "Ireland": r"\bireland\b|\bdublin\b",
    "Spain": r"\bspain\b|\bmadrid\b|\bbarcelona\b", "Portugal": r"\bportugal\b|\blisbon\b",
    "Poland": r"\bpoland\b|\bwarsaw\b", "Switzerland": r"\bswitzerland\b|\bz[uü]rich\b",
    "Sweden": r"\bsweden\b|\bstockholm\b", "Israel": r"\bisrael\b|\btel\s+aviv\b",
    "India": r"\bindia\b|\bbengaluru\b|\bbangalore\b|\bhyderabad\b|\bpune\b|\bmumbai\b|\bdelhi\b",
    "Singapore": r"\bsingapore\b", "Japan": r"\bjapan\b|\btokyo\b",
    "Australia": r"\baustralia\b|\bsydney\b|\bmelbourne\b", "Mexico": r"(?<!new )\bmexico\b",  # not New Mexico
    "Brazil": r"\bbrazil\b|\bs[aã]o\s+paulo\b",
    # Regions: a role limited to one of these is not in the United States.
    "Europe": r"\beurope\b|\bemea\b|\beu\b", "Asia-Pacific": r"\bapac\b", "Latin America": r"\blatam\b",
}
_PLACE_PATTERNS = {name: re.compile(p, re.IGNORECASE) for name, p in PLACE_PATTERNS.items()}


def posting_countries(posting: Posting) -> set[str]:
    """Countries/regions a posting names: structured (Ashby) plus place names in its locations."""
    text = " | ".join(posting.locations)
    return set(posting.countries) | {name for name, pattern in _PLACE_PATTERNS.items() if pattern.search(text)}


def _country_ok(posting: Posting, country: str | None) -> bool:
    """True when the posting is in ``country``, or names no country at all (unknown is kept)."""
    wanted = normalize_country(country)
    if not wanted:
        return True
    known = posting_countries(posting)
    if not known:
        return True
    return wanted in known or wanted.lower() in " | ".join(posting.locations).lower()


def _location_ok(posting: Posting, locations, remote: bool) -> bool:
    """Remote (if asked) AND any of `locations` (case-insensitive substring; 'remote' = remote work)."""
    places = " | ".join(posting.locations).lower()
    is_remote = posting.workplace == "remote" or "remote" in places
    if remote and not is_remote:
        return False
    if isinstance(locations, str):
        locations = [locations]
    wanted = [l.lower().strip() for l in locations or () if l and l.strip()]
    return not wanted or any(w in places or (w == "remote" and is_remote) for w in wanted)


def rank(postings, resume_skills: set[str], query: str, *, min_title_match: float = 0.6,
         location=None, remote: bool = False, max_years: int | None = None,
         no_senior: bool = False, country: str | None = None) -> list[Match]:
    """Score relevant postings and return them best first.

    location: one string or a list (any may match). max_years drops postings that
    ask for more years of experience; postings that state none are kept. country
    (e.g. "United States") drops postings known to be elsewhere, including remote
    roles abroad; postings that name no country are kept.
    """
    if not words(query):
        raise ValueError("The search needs at least one word, e.g. 'applied ai engineer'.")
    matches = []
    for posting in postings:
        relevance = title_match(query, posting.title)
        if (relevance < min_title_match or not _location_ok(posting, location, remote)
                or not _country_ok(posting, country) or (no_senior and is_senior_title(posting.title))):
            continue
        asked = years_asked(posting.description)
        if max_years is not None and asked is not None and asked > max_years:
            continue
        job_skills = extract_skills(posting.title + "\n" + posting.description)
        matched = sorted(job_skills & resume_skills)
        missing = sorted(job_skills - resume_skills)
        coverage = len(matched) / (len(job_skills) + SMOOTHING)
        score = round(100 * (TITLE_WEIGHT * relevance + SKILL_WEIGHT * coverage))
        matches.append(Match(score, relevance, coverage, tuple(matched), tuple(missing), asked, posting))
    matches.sort(key=lambda m: (m.score, m.title_match, m.posting.published_at or ""), reverse=True)
    return group_duplicates(matches)


def group_duplicates(matches: list[Match]) -> list[Match]:
    """One row per (source, company, title): the best-scoring posting, with every location.

    Boards often post the same role once per city (seen live: one role in 5 countries).
    The row keeps the best posting's link and score and counts the others.
    """
    from dataclasses import replace

    groups: dict[tuple, list[Match]] = {}
    for match in matches:  # already best first
        p = match.posting
        groups.setdefault((p.source, p.company, " ".join(p.title.lower().split())), []).append(match)
    grouped = []
    for members in groups.values():
        best = members[0]
        places = list(dict.fromkeys(loc for m in members for loc in m.posting.locations))
        grouped.append(replace(best, posting=replace(best.posting, locations=tuple(places)),
                               other_postings=len(members) - 1))
    grouped.sort(key=lambda m: (m.score, m.title_match, m.posting.published_at or ""), reverse=True)
    return grouped


def age_days(iso: str | None, now: datetime | None = None) -> int | None:
    if not iso:
        return None
    try:
        moment = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, ((now or datetime.now(timezone.utc)) - moment).days)
