# Key worksheet — slot B

**Authored by hand, from the documents (FR-2).** This worksheet deliberately does
not tell you what the mechanism drew. If the key agrees with the mechanism because
it was copied from it, precision and recall measure nothing.

Corpus status: **PILOT - INCOMPLETE**

## 1. The documents

| source_id | published | citation |
|---|---|---|
| `gamow1956` | 1956-09-01 | Gamow, George. "The Evolutionary Universe." Scientific American 195, no. 3 (September 1956): 136-156. |
| `gamow1970` | 1970-01-01 | Gamow, George. My World Line: An Informal Autobiography. New York: Viking Press, 1970, p. 44. |
| `alpher1998` | 1998-01-01 | Alpher, Ralph A. Posting to the History of Astronomy Listserve (HASTRO-L), 1998, in reply to a query from Joseph S. Tenn. Reproduced in full as Figure 7 of O'Raifeartaigh & Mitton 2018. |
| `wheeler2000` | 2000-01-01 | Taylor, Edwin F., and John Archibald Wheeler. Exploring Black Holes: Introduction to General Relativity. San Francisco: Addison Wesley Longman, 2000. |
| `livio2013` | 2013-01-01 | Livio, Mario. Brilliant Blunders: From Darwin to Einstein. New York: Simon & Schuster, 2013, ch. 10. |
| `oraifeartaigh2018` | 2018-01-01 | O'Raifeartaigh, Cormac, and Simon Mitton. "Interrogating the legend of Einstein's 'biggest blunder'." Physics in Perspective 20 (2018): 318-341. arXiv:1804.06768v2. |

## 2. The claim-instances, oldest first

Direction comes from these dates and nothing else.

### `B.gamow1956.c1`

- **published** 1956-09-01 · **locus** §unresolved
- **attributed_to** `Albert Einstein`

> Einstein remarked to me many years ago that the cosmic repulsion idea was the biggest blunder he had made in his entire life.

### `B.gamow1970.c1`

- **published** 1970-01-01 · **locus** §p44
- **attributed_to** `Albert Einstein`

> Much later, when I was discussing cosmological problems with Einstein, he remarked that the introduction of the cosmological term was the biggest blunder he ever made in his life.

### `B.gamow1970.c2`

- **published** 1970-01-01 · **locus** §p44.cont
- **attributed_to** `Albert Einstein`
- **note** The QUOTATION MARKS around 'blunder' are Livio's central evidence that Gamow meant to be quoting rather than paraphrasing -- and Livio still concludes against authenticity.

> But this "blunder," rejected by Einstein, is still sometimes used by cosmologists even today, and the cosmological constant denoted by the Greek letter "Λ" rears its ugly head again and again.

### `B.alpher1998.c1`

- **published** 1998-01-01 · **locus** §hastro-l
- **attributed_to** `Albert Einstein`
- **note** Hedged at the source -- 'as I recall' -- by the only witness who hedges.

> A way to fix this was to reactivate the cosmological constant. Einstein did not like this very much, and, as I recall, said his introduction of the concept in his early work was a blunder

### `B.wheeler2000.c1`

- **published** 2000-01-01 · **locus** §pG-11
- **attributed_to** `Albert Einstein`
- **note** Claimed FIRST-HAND, not via Gamow, while placing Gamow at the scene.

> Going into the doorway of the Institute for Advanced Study's Fuld Hall with Einstein and George Gamow, I heard Einstein say to Gamow about the cosmological constant, "That was my biggest blunder of my life."

### `B.livio2013.q_gamow`

- **published** 2013-01-01 · **locus** §ch10
- **attributed_to** `George Gamow`

> In an article entitled "The Evolutionary Universe," published in the September 1956 issue of Scientific American, Gamow wrote, "Einstein remarked to me many years ago that the cosmic repulsion idea was the biggest blunder he had made in his entire life."

### `B.livio2013.verdict`

- **published** 2013-01-01 · **locus** §ch10.verdict
- **attributed_to** *(none)*
- **note** Livio names NO ONE as the source of the phrase except Gamow himself, and calls it 'Gamow's own hyperbole'.

> my best guess, based on the entire body of evidence, is that while Einstein may have had a "bad conscience" about the introduction of the cosmological constant, especially since he missed the chance to predict the cosmic expansion, he never actually called it "the biggest blunder" that he "had ever made."

### `B.oraifeartaigh2018.q_alpher`

- **published** 2018-01-01 · **locus** §6.iv
- **attributed_to** `Albert Einstein, via Ralph Alpher`

> A way to fix this was to reactivate the cosmological constant. Einstein did not like this very much, and, as I recall, said his introduction of the concept in his early work was a blunder

### `B.oraifeartaigh2018.q_gamow`

- **published** 2018-01-01 · **locus** §4
- **attributed_to** `George Gamow`

> In a substantial article on 'big bang' cosmology published in Scientific American in May 1956, the Russian émigré physicist George Gamow reported: "Einstein remarked to me many years ago that the cosmic repulsion idea was the biggest blunder he had made in his entire life"

### `B.oraifeartaigh2018.q_wheeler`

- **published** 2018-01-01 · **locus** §6.iv
- **attributed_to** `Albert Einstein, via John Archibald Wheeler`

> Going into the doorway of the Institute for Advanced Study's Fuld Hall with Einstein and George Gamow, I heard Einstein say to Gamow about the cosmological constant, "That was my biggest blunder of my life."

### `B.oraifeartaigh2018.verdict`

- **published** 2018-01-01 · **locus** §abstract
- **attributed_to** *(none)*

> We conclude that there is little doubt that Einstein came to view the introduction of the cosmological constant term a serious error and that it is very likely that he labelled the term his "biggest blunder" on at least one occasion.

## 3. Spans as transcribed

Your own transcription, repeated here so you need not open the corpus file.
A shared span is evidence, not a verdict — you decide whether it means descent.

| span | appears in | text |
|---|---|---|
| `blunder_phrase` | `gamow1956`, `gamow1970`, `livio2013`, `oraifeartaigh2018` | was the biggest blunder he |
| `wheeler_doorway` | `wheeler2000`, `oraifeartaigh2018` | Going into the doorway of the Institute for Advanced Study's Fuld Hall with Einstein and G |
| `alpher_recall` | `alpher1998`, `oraifeartaigh2018` | his introduction of the concept in his early work was a blunder |

## 4. Asserted descents

A **third** document asserting a descent is what makes an edge `testimony`
rather than `textual`. An assertion by one of the endpoints is not testimony.

- **`gamow1956_attributes_blunder_to_einstein`** — asserted by `gamow1956`  
  claims: einstein -> the blunder phrase
- **`gamow1970_attributes_blunder_to_einstein`** — asserted by `gamow1970`  
  claims: einstein -> the blunder phrase
- **`wheeler_claims_direct_hearing`** — asserted by `wheeler2000`  
  claims: einstein -> the blunder phrase, on independent first-hand authority
- **`alpher_claims_direct_hearing`** — asserted by `alpher1998`  
  claims: einstein -> a blunder, on independent first-hand authority
- **`livio_concludes_fabrication`** — asserted by `livio2013`  
  claims: NO edge: gamow1956 has no ancestor in Einstein
- **`om_concludes_authentic`** — asserted by `oraifeartaigh2018`  
  claims: einstein -> the blunder phrase, on the weight of three independent reports
- **`om_raises_gamow_to_wheeler`** — asserted by `oraifeartaigh2018`  
  claims: gamow1956 -> wheeler2000, EXPLICITLY UNDETERMINED
- **`om_raises_gamow_to_alpher`** — asserted by `oraifeartaigh2018`  
  claims: gamow1956 -> alpher1998, EXPLICITLY UNDETERMINED
- **`livio_asserts_segre_folsing_repeat`** — asserted by `livio2013`  
  claims: gamow1970 -> segre2011 and gamow1970 -> folsing1997

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
| 1 | `B.gamow1956.c1` | `B.gamow1970.c1` |  |  |  |  |  |
| 2 | `B.gamow1956.c1` | `B.gamow1970.c2` |  |  |  |  |  |
| 3 | `B.gamow1956.c1` | `B.alpher1998.c1` |  |  |  |  |  |
| 4 | `B.gamow1956.c1` | `B.wheeler2000.c1` |  |  |  |  |  |
| 5 | `B.gamow1956.c1` | `B.livio2013.q_gamow` |  |  |  |  |  |
| 6 | `B.gamow1956.c1` | `B.livio2013.verdict` |  |  |  |  |  |
| 7 | `B.gamow1956.c1` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 8 | `B.gamow1956.c1` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 9 | `B.gamow1956.c1` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 10 | `B.gamow1956.c1` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 11 | `B.gamow1970.c1` | `B.alpher1998.c1` |  |  |  |  |  |
| 12 | `B.gamow1970.c1` | `B.wheeler2000.c1` |  |  |  |  |  |
| 13 | `B.gamow1970.c1` | `B.livio2013.q_gamow` |  |  |  |  |  |
| 14 | `B.gamow1970.c1` | `B.livio2013.verdict` |  |  |  |  |  |
| 15 | `B.gamow1970.c1` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 16 | `B.gamow1970.c1` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 17 | `B.gamow1970.c1` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 18 | `B.gamow1970.c1` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 19 | `B.gamow1970.c2` | `B.alpher1998.c1` |  |  |  |  |  |
| 20 | `B.gamow1970.c2` | `B.wheeler2000.c1` |  |  |  |  |  |
| 21 | `B.gamow1970.c2` | `B.livio2013.q_gamow` |  |  |  |  |  |
| 22 | `B.gamow1970.c2` | `B.livio2013.verdict` |  |  |  |  |  |
| 23 | `B.gamow1970.c2` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 24 | `B.gamow1970.c2` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 25 | `B.gamow1970.c2` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 26 | `B.gamow1970.c2` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 27 | `B.alpher1998.c1` | `B.wheeler2000.c1` |  |  |  |  |  |
| 28 | `B.alpher1998.c1` | `B.livio2013.q_gamow` |  |  |  |  |  |
| 29 | `B.alpher1998.c1` | `B.livio2013.verdict` |  |  |  |  |  |
| 30 | `B.alpher1998.c1` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 31 | `B.alpher1998.c1` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 32 | `B.alpher1998.c1` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 33 | `B.alpher1998.c1` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 34 | `B.wheeler2000.c1` | `B.livio2013.q_gamow` |  |  |  |  |  |
| 35 | `B.wheeler2000.c1` | `B.livio2013.verdict` |  |  |  |  |  |
| 36 | `B.wheeler2000.c1` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 37 | `B.wheeler2000.c1` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 38 | `B.wheeler2000.c1` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 39 | `B.wheeler2000.c1` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 40 | `B.livio2013.q_gamow` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 41 | `B.livio2013.q_gamow` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 42 | `B.livio2013.q_gamow` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 43 | `B.livio2013.q_gamow` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |
| 44 | `B.livio2013.verdict` | `B.oraifeartaigh2018.q_alpher` |  |  |  |  |  |
| 45 | `B.livio2013.verdict` | `B.oraifeartaigh2018.q_gamow` |  |  |  |  |  |
| 46 | `B.livio2013.verdict` | `B.oraifeartaigh2018.q_wheeler` |  |  |  |  |  |
| 47 | `B.livio2013.verdict` | `B.oraifeartaigh2018.verdict` |  |  |  |  |  |

**47 decisions.**

Not decidable (8 same-document pairs):

- `B.gamow1970.c1` / `B.gamow1970.c2` — both in `gamow1970`
- `B.livio2013.q_gamow` / `B.livio2013.verdict` — both in `livio2013`
- `B.oraifeartaigh2018.q_alpher` / `B.oraifeartaigh2018.q_gamow` — both in `oraifeartaigh2018`
- `B.oraifeartaigh2018.q_alpher` / `B.oraifeartaigh2018.q_wheeler` — both in `oraifeartaigh2018`
- `B.oraifeartaigh2018.q_alpher` / `B.oraifeartaigh2018.verdict` — both in `oraifeartaigh2018`
- `B.oraifeartaigh2018.q_gamow` / `B.oraifeartaigh2018.q_wheeler` — both in `oraifeartaigh2018`
- `B.oraifeartaigh2018.q_gamow` / `B.oraifeartaigh2018.verdict` — both in `oraifeartaigh2018`
- `B.oraifeartaigh2018.q_wheeler` / `B.oraifeartaigh2018.verdict` — both in `oraifeartaigh2018`

## 6. Before you call it done

- [ ] Every `y` row has a `why` that quotes or cites the documents.
- [ ] No row has two mutation operators.
- [ ] `testimony` only where a document that is **neither endpoint** asserts it.
- [ ] Direction checked against the dates in §1, not against plausibility.
- [ ] You have not looked at any reconstruction output.
