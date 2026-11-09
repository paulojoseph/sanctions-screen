# Architecture

Notes for people who want to change the code. Last big edit: 0.2 era, touched up since.

## Overview

`sanctions-screen` is a pipeline with four stages:

1. **Fetch** the public lists (OFAC, UN, EU, UK) into `data/lists/`.
2. **Parse** each list into the unified `Entity` model.
3. **Store** the entities and the normalized names in a local SQLite database
   (`data/sanctions.db`) so that screening does not re-parse the XML every time.
4. **Screen** names against the store and explain every hit.

Everything runs offline except stage 1.

## Layout

```
src/sanctions_screen/
  model.py            Entity, Alias, Dob, IdDocument
  ofac.py un.py eu.py uk.py local.py     one parser per source
  normalize.py        text normalization (comments in Portuguese)
  transliteration.py  Cyrillic / Arabic -> Latin
  match.py            name-to-name scoring
  index.py            in-memory index + gzip JSON persistence
  screen.py           screening, DOB / country adjustments, reports
  batch.py            customer CSV -> report.json / report.csv
  diff.py             compare two list snapshots
  decisions.py        reviewer decisions
  fetch.py            downloads
  api.py              FastAPI app
  cli.py              typer app
```

## The store

The store is a SQLite database with three tables.

| table     | purpose                                  |
|-----------|------------------------------------------|
| entities  | one row per listed party                 |
| names     | one row per name or alias, with its tokens and phonetic key |
| dobs      | one row per date of birth                |

`sanctions-screen index` creates the database and `sanctions-screen screen` opens it
read-only. Rows are inserted in a single transaction per source, and the `names` table
has an index on the first token so candidate lookup is a single query.

Why SQLite: the first version kept everything in a Python dict, and starting the CLI took
four seconds. With SQLite the start-up is instant and the file can be shared between the
CLI and the API.

## The Entity model

Entities are pydantic models. The id is `source:uid`, for example `ofac:12345` or
`un:QDi.001`. The id is built in exactly one place (`model.make_id`) and the decisions
file depends on it, so it must not change.

An entity has:

- a primary name and a list of aliases (`strong` or `weak`)
- dates of birth: `full`, `year`, `circa` or `range`
- nationalities (ISO 3166 alpha-2)
- identity documents
- programs (sanctions regimes)
- the date of the list it came from

### Aliases

Weak aliases (OFAC "weak a.k.a.", UN quality "Low", EU `strong="false"`, UK "FKA") are
**not** scored at all. They are stored for display only, so a reviewer can see them next
to a hit, but they never produce a hit by themselves.

## Parsing

Each parser takes a path and returns `list[Entity]`.

- **OFAC** `SDN.XML`: namespace `http://tempuri.org/sdnList.xsd`.
- **UN** consolidated XML: `INDIVIDUALS` and `ENTITIES`.
- **EU** FSF XML: `sanctionEntity` with `nameAlias`.
- **UK** CSV: one row per name, grouped by Group ID.
- **local**: `data/lists/local_watchlist.csv`.

Parsers raise `ParseError` when a file does not look right and report the file name.
The older parsers (OFAC and UN) print a message and skip a record instead.

## Normalization

`normalize.normalize()` does, in order:

1. Unicode NFKD, strip combining marks
2. lowercase
3. transliterate Cyrillic and Arabic
4. remove punctuation, split on spaces and hyphens
5. drop honorifics and legal forms
6. drop Iberian particles (de, da, do, dos, das, del)

The same function is applied to the index and to the query so both sides always agree.

## Scoring

`match.match_name(query, candidate, mode)` returns a `MatchScore`. Three modes exist:
`strict`, `balanced` and `broad`.

The score is a blend of the sorted-token Jaro-Winkler similarity, a token coverage
measure and a phonetic key comparison. The weights live in `config.py`.

On top of the name score, `screen.py` adjusts for date of birth and country:

| situation                         | adjustment |
|-----------------------------------|-----------:|
| DOB matches                       | +0.06      |
| DOB differs by a typo (<= 45 days)| 0          |
| DOB differs                       | -0.10      |
| country matches a nationality     | +0.02      |
| country differs                   | -0.03      |

Adjustments are applied by one function (`_score_record`) shared by the CLI, the API and
the batch command, so all three always give the same answer.

## Batch

`batch.run_batch()` reads the customer CSV, calls `screen.screen_name()` for each row and
writes `report.json` and `report.csv`. Because it reuses `screen_name()`, batch results are
identical to what `screen` prints for the same row.

Rows are processed in parallel with a process pool; the number of workers defaults to the
number of CPUs.

## Decisions

A reviewer decision says that a given customer is not a given listed entity. It is stored
as one JSON line in `data/decisions/decisions.jsonl` with the customer reference and the
entity id. During screening, pairs found in the file are removed from the hits.

The decision file is append-only and should be committed.

## The API

`api.py` exposes `GET /health` and `POST /screen`. The app loads the index once, at
start-up, and holds it in memory. If the index is missing it answers 503.

## Index format

`data/index.json.gz` holds the entities and the name records. `INDEX_FORMAT` is bumped when
the layout changes and `load_index` refuses older versions with a message to rebuild.

## Testing

- Parsers are tested against the fixtures in `tests/fixtures/lists/`.
- The golden test (`tests/golden/expected_hits.json`) pins the library path.
- Tests never touch the network.

## Configuration

Every threshold lives in `config.py`. Nothing else should hard-code a number that changes
results. Environment variables are not used.

## Error handling

All errors derive from `SanctionsScreenError` and the CLI turns them into exit code 2 with a
one-line message. Unexpected exceptions print a traceback.

## Performance notes

- Candidate lookup uses the first-token index in SQLite, then rescoring in Python.
- A 10k-row batch takes under a minute on a laptop.
- `index_v2.py` is an experiment with a token inverted index, not wired in yet.

## Things we decided not to do

- No machine learning model. Reviewers need to be able to read an explanation.
- No automatic download on `screen`; the lists change when the operator says so.
- No web UI.

## CLI commands

| command  | what it does                                                        |
|----------|---------------------------------------------------------------------|
| fetch    | downloads the lists into `data/lists/` (the only command that uses the network) |
| index    | parses the lists and writes `data/index.json.gz`                    |
| screen   | screens one name, optional `--dob` and `--country`                  |
| batch    | screens a customer CSV and writes `report.json` and `report.csv`    |
| diff     | compares two list snapshots (added, removed, changed entities)      |
| serve    | runs the API with uvicorn                                           |

Thresholds are 0-100 on the command line and 0-1 in the library.

## Sources

| source | format | key               |
|--------|--------|-------------------|
| OFAC   | XML    | `uid`             |
| UN     | XML    | `REFERENCE_NUMBER`|
| EU     | XML    | `logicalId`       |
| UK     | CSV    | `Group ID`        |

## Adding a new source

1. Write `src/sanctions_screen/<source>.py` with a function that returns `list[Entity]`.
2. Register it in `LIST_FILES` in `screen.py`.
3. Add a fixture in the publisher's exact format to `scripts/make_fixtures.py`.
4. Add `tests/test_<source>.py`.
