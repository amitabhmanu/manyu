# Key worksheet — slot E

**Authored by hand, from the documents (FR-2).** This worksheet deliberately does
not tell you what the mechanism drew. If the key agrees with the mechanism because
it was copied from it, precision and recall measure nothing.

Corpus status: **PILOT - INCOMPLETE**

## 1. The documents

| source_id | published | citation |
|---|---|---|
| `bender1972` | 1972-10-24 | Bender, Arnold E. The Wider Knowledge of Nutrition. Inaugural Lecture, 24 October 1972, Queen Elizabeth College, University of London. London: Castle Cary Press, 1972, p. 11. |
| `bender1977` | 1977-07-09 | Bender, Arnold E. "Iron in spinach." The Spectator, 9 July 1977, p. 18. |
| `hamblin1981` | 1981-12-19 | Hamblin, T. J. "Fake!" British Medical Journal 283, no. 6307 (19-26 December 1981): 1671-1674. |
| `larsson1995` | 1995-01-01 | Larsson, Hans. Cited by Rekdal as Larsson 1995: 448-449. The intermediate link Rekdal names between Hamblin and himself. NOT OBTAINED. |
| `rekdal2014` | 2014-06-12 | Rekdal, Ole Bjorn. "Academic urban legends." Social Studies of Science 44, no. 4 (2014): 638-654. DOI 10.1177/0306312714535679. OnlineFirst 12 June 2014. |

## 2. The claim-instances, oldest first

Direction comes from these dates and nothing else.

### `E.bender1972.c1`

- **published** 1972-10-24 · **locus** §p11
- **attributed_to** *(none)*

> the fame of spinach may well have grown from a misplaced decimal point

### `E.bender1977.c1`

- **published** 1977-07-09 · **locus** §p18
- **attributed_to** *(none)*

> The fame of spinach appears to have been based on a misplaced decimal point

### `E.hamblin1981.c1`

- **published** 1981-12-19 · **locus** §p1671
- **attributed_to** *(none)*
- **note** Names NO ONE -- only 'German chemists' and 'the original workers'. Confirmed by a peer-reviewed source.

> German chemists reinvestigating the iron content of spinach had shown in the 1930s that the original workers had put the decimal point in the wrong place and made a tenfold overestimate of its value.

### `E.rekdal2014.p640_bare`

- **published** 2014-06-12 · **locus** §p640.a
- **attributed_to** *(none)*
- **note** Attributed to NOBODY. Rekdal's point is that a reader would take him for the discoverer.

> The idea that spinach is a good source of iron is a myth that was born in the 1930s, due to a misplaced decimal point, causing the concentration to appear ten times higher than its real value.

### `E.rekdal2014.p640_larsson`

- **published** 2014-06-12 · **locus** §p640.b
- **attributed_to** `Hans Larsson`
- **note** The HONEST citation, and the one Rekdal endorses.

> The idea that spinach is a good source of iron is a myth that was born in the 1930s, due to a misplaced decimal point, causing the concentration to appear ten times higher than its real value (Larsson, 1995: 448-449).

### `E.rekdal2014.p642_hamblin`

- **published** 2014-06-12 · **locus** §p642
- **attributed_to** `T. J. Hamblin`
- **note** A citation the author DECLARES to be false while making it. The corpus records what the document says, and what it says is Hamblin.

> The idea that spinach is a good source of iron is a myth that was born in the 1930s, due to a misplaced decimal point, causing the concentration to appear ten times higher than its real value (Hamblin, 1981).

## 3. Spans as transcribed

Your own transcription, repeated here so you need not open the corpus file.
A shared span is evidence, not a verdict — you decide whether it means descent.

| span | appears in | text |
|---|---|---|
| `fame_of_spinach` | `bender1972`, `bender1977` | fame of spinach |
| `misplaced_decimal_point` | `bender1972`, `bender1977` | a misplaced decimal point |
| `rekdal_myth_sentence` | `rekdal2014` | The idea that spinach is a good source of iron is a myth that was born in the 1930s, due t |

## 4. Asserted descents

A **third** document asserting a descent is what makes an edge `testimony`
rather than `textual`. An assertion by one of the endpoints is not testimony.

- **`hamblin_asserts_decimal_origin`** — asserted by `hamblin1981`  
  claims: an UNNAMED 19th-century analysis -> the iron-rich claim
- **`rekdal_asserts_bender_to_hamblin`** — asserted by `rekdal2014`  
  claims: bender1972/1977 -> hamblin1981
- **`rekdal_asserts_hamblin_to_larsson`** — asserted by `rekdal2014`  
  claims: hamblin1981 -> larsson1995
- **`rekdal_asserts_larsson_to_himself`** — asserted by `rekdal2014`  
  claims: larsson1995 -> rekdal2014

## 5. Decisions

One row per ordered pair, older → newer. Same-document pairs are listed but need
no decision: two loci of one document are siblings, never ancestor and descendant.

`edge?` — `y` / `n`. `support` — `textual` / `testimony`. `undet` — `y` if the
sources raise this descent and decline to settle it. `mutation` — **one** operator,
highest precedence only:

1. `attribution_shift` — `attributed_to` differs
2. `deletion` — the descendant's sentences are a proper subset of the ancestor's
3. `qualification` — the hedge set differs
4. `rewording` — the excerpts differ and nothing above applies
5. `none` — identical modulo whitespace and case

| # | ancestor | descendant | edge? | support | mutation | undet | why (quote the documents) |
|---|---|---|---|---|---|---|---|
| 1 | `E.bender1972.c1` | `E.bender1977.c1` |  |  |  |  |  |
| 2 | `E.bender1972.c1` | `E.hamblin1981.c1` |  |  |  |  |  |
| 3 | `E.bender1972.c1` | `E.rekdal2014.p640_bare` |  |  |  |  |  |
| 4 | `E.bender1972.c1` | `E.rekdal2014.p640_larsson` |  |  |  |  |  |
| 5 | `E.bender1972.c1` | `E.rekdal2014.p642_hamblin` |  |  |  |  |  |
| 6 | `E.bender1977.c1` | `E.hamblin1981.c1` |  |  |  |  |  |
| 7 | `E.bender1977.c1` | `E.rekdal2014.p640_bare` |  |  |  |  |  |
| 8 | `E.bender1977.c1` | `E.rekdal2014.p640_larsson` |  |  |  |  |  |
| 9 | `E.bender1977.c1` | `E.rekdal2014.p642_hamblin` |  |  |  |  |  |
| 10 | `E.hamblin1981.c1` | `E.rekdal2014.p640_bare` |  |  |  |  |  |
| 11 | `E.hamblin1981.c1` | `E.rekdal2014.p640_larsson` |  |  |  |  |  |
| 12 | `E.hamblin1981.c1` | `E.rekdal2014.p642_hamblin` |  |  |  |  |  |

**12 decisions.**

Not decidable (3 same-document pairs):

- `E.rekdal2014.p640_bare` / `E.rekdal2014.p640_larsson` — both in `rekdal2014`
- `E.rekdal2014.p640_bare` / `E.rekdal2014.p642_hamblin` — both in `rekdal2014`
- `E.rekdal2014.p640_larsson` / `E.rekdal2014.p642_hamblin` — both in `rekdal2014`

## 6. Before you call it done

- [ ] Every `y` row has a `why` that quotes or cites the documents.
- [ ] No row has two mutation operators.
- [ ] `testimony` only where a document that is **neither endpoint** asserts it.
- [ ] Direction checked against the dates in §1, not against plausibility.
- [ ] You have not looked at any reconstruction output.
