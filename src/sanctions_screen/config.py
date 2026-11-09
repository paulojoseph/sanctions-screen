"""All tunable thresholds live here. Keep it that way."""

from pathlib import Path

# --- matching thresholds (library scale: 0.0 - 1.0) ---------------------------------------
DEFAULT_THRESHOLD = 0.80  # minimum final score for a hit
STRICT_MIN_COVERAGE = 0.99  # strict mode: every token of the query has to find a partner
TOKEN_MATCH_MIN = 0.85  # jaro-winkler needed for two tokens to count as "the same token"
MAX_HITS = 10  # per screened name, after sorting
MIN_NAME_LENGTH = 3  # shorter normalized queries are not screened at all
CANDIDATE_FLOOR = 0.55  # cheap prefilter score a name must clear before the full scorer runs
STALE_LIST_DAYS = 14  # warn when a list is older than this
RELATED_NAME_MIN = 0.90  # primary names this close may be one party listed by two sources
BAND_STRONG = 0.95  # label cutoffs for the text output, nothing else reads these
BAND_LIKELY = 0.88
VESSEL_MIN_SCORE = 0.92  # vessels and aircraft are only worth a hit on a near-exact name
DOB_TYPO_DAYS = 45  # two full dates this close are treated as a typo: no boost, no penalty

# --- score blend ------------------------------------------------------------------------
W_SORT = 0.45
W_COVERAGE = 0.40
W_PHONETIC = 0.15

# --- paths ------------------------------------------------------------------------------
DEFAULT_LISTS_DIR = Path("data/lists")
DEFAULT_INDEX_PATH = Path("data/index.json.gz")
DEFAULT_DECISIONS_PATH = Path("data/decisions/decisions.jsonl")

# --- network (fetch only) ---------------------------------------------------------------
FETCH_TIMEOUT_SECONDS = 120.0
USER_AGENT = "sanctions-screen/0.4"
