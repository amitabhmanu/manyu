# Key worksheet — slot A

**Authored by hand, from the documents (FR-2).** This worksheet deliberately does
not tell you what the mechanism drew. If the key agrees with the mechanism because
it was copied from it, precision and recall measure nothing.

Corpus status: **PILOT - INCOMPLETE**

## 1. The documents

| source_id | published | citation |
|---|---|---|
| `fnb1945` | 1945-08-01 | Food and Nutrition Board, National Academy of Sciences. Recommended Dietary Allowances, revised 1945. National Research Council, Reprint and Circular Series No. 122, 1945 (Aug), pp. 3-18. |
| `valtin2002` | 2002-11-01 | Valtin, Heinz. "'Drink at least eight glasses of water a day.' Really?" American Journal of Physiology 283, no. 5 (2002): R993-R1004. |
| `vreeman2007` | 2007-12-22 | Vreeman, Rachel C., and Aaron E. Carroll. "Medical myths." BMJ 335, no. 7633 (22 December 2007): 1288-1289. Not commissioned; not externally peer reviewed. |
| `carroll2015` | 2015-08-24 | Carroll, Aaron E. "No, You Do Not Have to Drink 8 Glasses of Water a Day." The New York Times (The Upshot), 24 August 2015. Print version 25 August 2015, Section A, p. 3, under a different headline. |

## 2. The claim-instances, oldest first

Direction comes from these dates and nothing else.

### `A.fnb1945.rec1`

- **published** 1945-08-01 · **locus** §rec.1
- **attributed_to** *(none)*

> A suitable allowance of water for adults is 2.5 liters daily in most instances. An ordinary standard for diverse persons is one milliliter for each calorie of food. Most of this quantity is contained in prepared foods.

### `A.fnb1945.rec2`

- **published** 1945-08-01 · **locus** §rec.2
- **attributed_to** *(none)*

> Water should be allowed ad libitum, since sensations of thirst usually serve as adequate guides to intake except for infants and sick persons.

### `A.valtin2002.c1`

- **published** 2002-11-01 · **locus** §POSSIBLE ORIGIN OF 8 × 8
- **attributed_to** *(none)*

> A suitable allowance of water for adults is 2.5 liters daily in most instances. An ordinary standard for diverse persons is 1 milliliter for each calorie of food. Most of this quantity is contained in prepared foods.

### `A.valtin2002.q_stare`

- **published** 2002-11-01 · **locus** §POSSIBLE ORIGIN OF 8 × 8
- **attributed_to** `Frederick J. Stare and Margaret McWilliams`
- **note** Valtin names BOTH coauthors, in the text and again in his reasons against.

> How much water each day? This is usually well regulated by various physiological mechanisms, but for the average adult, somewhere around 6 to 8 glasses per 24 hours and this can be in the form of coffee, tea, milk, soft drinks, beer, etc. Fruits and vegetables are also good sources of water.

### `A.vreeman2007.c1`

- **published** 2007-12-22 · **locus** §myth.1 (p. 1288)
- **attributed_to** `Heinz Valtin`

> A suitable allowance of water for adults is 2.5 litres daily in most instances. An ordinary standard for diverse persons is 1 millilitre for each calorie of food. Most of this quantity is contained in prepared foods.

### `A.vreeman2007.q_stare`

- **published** 2007-12-22 · **locus** §myth.1 (p. 1288)
- **attributed_to** `Frederick Stare`
- **note** The coauthor is GONE. Valtin's 'Drs. Stare and McWilliams' becomes 'a prominent nutritionist, Frederick Stare' -- a real attribution shift, five years and one hop downstream, and the second one slot A carries.

> Another endorsement may have come from a prominent nutritionist, Frederick Stare, who once recommended, without references, the consumption “around 6 to 8 glasses per 24 hours,” which could be “in the form of coffee, tea, milk, soft drinks, beer, etc.”

### `A.carroll2015.c1`

- **published** 2015-08-24 · **locus** §unresolved
- **attributed_to** *(none)*
- **note** Cited by hyperlink to Valtin's paper, never named in the body text. The field records what the document SAYS, and it says no name.

> Most of this quantity is contained in prepared foods.

## 3. Spans as transcribed

Your own transcription, repeated here so you need not open the corpus file.
A shared span is evidence, not a verdict — you decide whether it means descent.

| span | appears in | text |
|---|---|---|
| `prepared_foods` | `fnb1945`, `valtin2002`, `vreeman2007`, `carroll2015` | Most of this quantity is contained in prepared foods. |
| `allowance_liters` | `fnb1945`, `valtin2002` | A suitable allowance of water for adults is 2.5 liters daily in most instances. |
| `thirst_qualifier` | `fnb1945` | Water should be allowed ad libitum, since sensations of thirst usually serve as adequate g |
| `stare_6to8` | `valtin2002`, `vreeman2007` | around 6 to 8 glasses per 24 hours |
| `stare_beverages` | `valtin2002`, `vreeman2007` | in the form of coffee, tea, milk, soft drinks, beer, etc. |

## 4. Asserted descents

A **third** document asserting a descent is what makes an edge `testimony`
rather than `textual`. An assertion by one of the endpoints is not testimony.

- **`thomas_asserts_fnb_origin`** — asserted by `valtin2002`  
  claims: fnb1945 -> the 8x8 claim
- **`valtin_floats_stare_origin`** — asserted by `valtin2002`  
  claims: stare1974 -> the 8x8 claim
- **`vc_asserts_fnb_origin`** — asserted by `vreeman2007`  
  claims: fnb1945 -> the 8x8 claim
- **`vc_asserts_stare_origin`** — asserted by `vreeman2007`  
  claims: stare1974 -> the 8x8 claim

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
| 1 | `A.fnb1945.rec1` | `A.valtin2002.c1` |  |  |  |  |  |
| 2 | `A.fnb1945.rec1` | `A.valtin2002.q_stare` |  |  |  |  |  |
| 3 | `A.fnb1945.rec1` | `A.vreeman2007.c1` |  |  |  |  |  |
| 4 | `A.fnb1945.rec1` | `A.vreeman2007.q_stare` |  |  |  |  |  |
| 5 | `A.fnb1945.rec1` | `A.carroll2015.c1` |  |  |  |  |  |
| 6 | `A.fnb1945.rec2` | `A.valtin2002.c1` |  |  |  |  |  |
| 7 | `A.fnb1945.rec2` | `A.valtin2002.q_stare` |  |  |  |  |  |
| 8 | `A.fnb1945.rec2` | `A.vreeman2007.c1` |  |  |  |  |  |
| 9 | `A.fnb1945.rec2` | `A.vreeman2007.q_stare` |  |  |  |  |  |
| 10 | `A.fnb1945.rec2` | `A.carroll2015.c1` |  |  |  |  |  |
| 11 | `A.valtin2002.c1` | `A.vreeman2007.c1` |  |  |  |  |  |
| 12 | `A.valtin2002.c1` | `A.vreeman2007.q_stare` |  |  |  |  |  |
| 13 | `A.valtin2002.c1` | `A.carroll2015.c1` |  |  |  |  |  |
| 14 | `A.valtin2002.q_stare` | `A.vreeman2007.c1` |  |  |  |  |  |
| 15 | `A.valtin2002.q_stare` | `A.vreeman2007.q_stare` |  |  |  |  |  |
| 16 | `A.valtin2002.q_stare` | `A.carroll2015.c1` |  |  |  |  |  |
| 17 | `A.vreeman2007.c1` | `A.carroll2015.c1` |  |  |  |  |  |
| 18 | `A.vreeman2007.q_stare` | `A.carroll2015.c1` |  |  |  |  |  |

**18 decisions.**

Not decidable (3 same-document pairs):

- `A.fnb1945.rec1` / `A.fnb1945.rec2` — both in `fnb1945`
- `A.valtin2002.c1` / `A.valtin2002.q_stare` — both in `valtin2002`
- `A.vreeman2007.c1` / `A.vreeman2007.q_stare` — both in `vreeman2007`

## 6. Before you call it done

- [ ] Every `y` row has a `why` that quotes or cites the documents.
- [ ] No row has two mutation operators.
- [ ] `testimony` only where a document that is **neither endpoint** asserts it.
- [ ] Direction checked against the dates in §1, not against plausibility.
- [ ] You have not looked at any reconstruction output.
