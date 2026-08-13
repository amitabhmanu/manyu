"""Build the slot A, B and E corpus files from the transcription of record.

Supersedes `build_corpus_a.py`. One builder for all three slots, because three
builders would let the file format drift between them and the scoring function
cannot tell a format difference from a finding.

**Not slot D's generator.** Slot D emits its corpus *and its key* from one
function, because the null must not drift from what scores it (FR-8). Here only
corpora are emitted; every `key_*.json` is hand-authored from the documents and
no model touches one (FR-2).

**Every excerpt below is HELD on the worksheet author's instruction that eye
confirmation is complete.** Provenance differs and is recorded per source: the
FNB and Bender loci are the author's own reading, `valtin2002` is a born-digital
PDF the author supplied, `vreeman2007` and `carroll2015` are publisher web text
the author read. Any one reverts with a single edit.

**Spans are recorded on the verbatim rule** — text shared character for
character. Where wording differs the span stops, because a span that absorbed a
variant would erase the mutation being measured. This is why slot A's
`allowance_liters` covers two documents and not three, and why neither
`wheeler2000` nor `hamblin1981` joins the span of the thing they are talking
about.

**An assertion's `cited_by` should be written EXPLICITLY.** The default -- every
claim-instance of the asserting document -- is safe only while that document has
one locus. Add a second and the assertion silently acquires two endpoints in the
same document, which forms no edge (siblings) *and* drops out of
`unresolved_assertions`, because that list reports assertions reaching fewer than
two instances. The assertion disappears. Slot A hit this the moment
`A.valtin2002.q_stare` was added, and A9 exists precisely to stop assertions
disappearing.

**`§unresolved` is a value, not a gap.** A held document whose locus is not
established records `§unresolved`, so an unknown page stays distinguishable from
one nobody needed.

Deterministic. No clock, no randomness, no provider.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
FIXTURES = REPO / "evals" / "fixtures" / "exp08"
UNRESOLVED = "§unresolved"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# =============================================================================
# SLOT A
# =============================================================================

A_FNB1 = (
    "A suitable allowance of water for adults is 2.5 liters daily in most instances. "
    "An ordinary standard for diverse persons is one milliliter for each calorie of food. "
    "Most of this quantity is contained in prepared foods."
)
A_FNB2 = (
    "Water should be allowed ad libitum, since sensations of thirst usually serve as "
    "adequate guides to intake except for infants and sick persons."
)
A_VALTIN = A_FNB1.replace("one milliliter", "1 milliliter")
A_VREEMAN = A_VALTIN.replace("liters", "litres").replace("milliliter", "millilitre")
A_CARROLL = "Most of this quantity is contained in prepared foods."

# The SECOND origin candidate, and the second textual family in slot A. Both
# documents quote Stare & McWilliams 1974, which is itself NOT HELD -- so the
# family exists entirely as quotation, and its edge runs between the two
# quoters rather than from the quoted. Exactly the shape A10 said slot A
# lacked: a rival origin with textual substance rather than a bare name.
A_VALTIN_STARE = (
    "How much water each day? This is usually well regulated by various physiological "
    "mechanisms, but for the average adult, somewhere around 6 to 8 glasses per 24 hours "
    "and this can be in the form of coffee, tea, milk, soft drinks, beer, etc. Fruits and "
    "vegetables are also good sources of water."
)
A_VREEMAN_STARE = (
    "Another endorsement may have come from a prominent nutritionist, Frederick Stare, who "
    "once recommended, without references, the consumption “around 6 to 8 glasses per 24 "
    "hours,” which could be “in the form of coffee, tea, milk, soft drinks, beer, etc.”"
)

# The PRINT text of the same two passages, from the publisher PDF of pp. 1288-1289.
# NOT built into instances -- recorded so the divergence is on the record and can be
# promoted to its own source the day the key author decides a printing is a document.
# The differences are small and every one of them is a mutation the scorer would see:
# "1 millilitre" (web) reads "1 ml" (print); "once recommended, the consumption" reads
# "recommended, the consumption of"; "Furthermore" reads "Also"; "In contrast" reads
# "But". The print carries NO reference markers at all -- "A full version with
# references is on bmj.com" -- so w1-w9 exist only in the web edition.
A_VREEMAN_PRINT_VARIANT = (
    "PRINT p. 1288 reads “...1 ml for each calorie of food...” where the web edition "
    "reads “1 millilitre”, and “recommended, without references, the consumption of” "
    "where the web edition reads “once recommended, without references, the consumption”."
)

SLOT_A: dict[str, Any] = {
    "slot": "A",
    "description": (
        "Slot A as narrowed by A10: calibration retained for the textually demonstrable "
        "half, origin edge undetermined between rivals. PILOT. Every document here is the "
        "origin or a correction. The propagators are now IDENTIFIED -- not from Vreeman & "
        "Carroll's w-list, which stayed behind a CAPTCHA, but from Valtin's own reference "
        "list, which is better because Valtin QUOTES them (refs 3, 17, 42, 54). They are "
        "still absent as nodes because every propagator excerpt available is RELAYED "
        "through Valtin, and only HELD is committable. Results demonstrate the pipeline "
        "and A6's confound, and demonstrate nothing about calibration."
    ),
    "sources": [
        ("fnb1945", "Food and Nutrition Board, National Academy of Sciences. Recommended Dietary Allowances, revised 1945. National Research Council, Reprint and Circular Series No. 122, 1945 (Aug), pp. 3-18.", "1945-08-01", "month", "origin candidate; contested (A10)"),
        ("valtin2002", "Valtin, Heinz. \"'Drink at least eight glasses of water a day.' Really?\" American Journal of Physiology 283, no. 5 (2002): R993-R1004.", "2002-11-01", "month", "investigation; reports the FNB origin at two removes and floats a SECOND, rival origin it then argues against"),
        ("vreeman2007", "Vreeman, Rachel C., and Aaron E. Carroll. \"Medical myths.\" BMJ 335, no. 7633 (22 December 2007): 1288-1289. Not commissioned; not externally peer reviewed.", "2007-12-22", "day", "correction; names Valtin (w8)"),
        ("carroll2015", "Carroll, Aaron E. \"No, You Do Not Have to Drink 8 Glasses of Water a Day.\" The New York Times (The Upshot), 24 August 2015. Print version 25 August 2015, Section A, p. 3, under a different headline.", "2015-08-24", "day", "correction; cites Valtin by hyperlink, never by name"),
    ],
    "spans": [
        ("prepared_foods", "Most of this quantity is contained in prepared foods.", ["fnb1945", "valtin2002", "vreeman2007", "carroll2015"], None),
        ("allowance_liters", "A suitable allowance of water for adults is 2.5 liters daily in most instances.", ["fnb1945", "valtin2002"], "Stops at two documents: vreeman2007 carries the British 'litres' and 'millilitre'. That difference is the mutation; absorbing it into the span would erase it."),
        ("thirst_qualifier", A_FNB2, ["fnb1945"], "Attested in ONE document. Neither Valtin nor Vreeman & Carroll quote this sentence. The weakest excerpt in slot A, and the one carrying the second deletion."),
        ("stare_6to8", "around 6 to 8 glasses per 24 hours", ["valtin2002", "vreeman2007"], "The rival origin's text, and it survives BOTH the web and print editions of vreeman2007 unchanged -- which is why the print variant does not break this span."),
        ("stare_beverages", "in the form of coffee, tea, milk, soft drinks, beer, etc.", ["valtin2002", "vreeman2007"], "The clause that DEFEATS the rival origin: Stare allowed the caffeinated drinks 8x8 forbids. Both investigators quote it, and neither propagator does."),
    ],
    "instances": [
        ("A.fnb1945.rec1", "fnb1945", "§rec.1", 'under "Further recommendations:", sub-label "Water."; page within pp. 3-18 unresolved', A_FNB1, ["prepared_foods", "allowance_liters"], None, None),
        ("A.fnb1945.rec2", "fnb1945", "§rec.2", "same paragraph, final sentence", A_FNB2, ["thirst_qualifier"], None, None),
        ("A.valtin2002.c1", "valtin2002", "§POSSIBLE ORIGIN OF 8 × 8", "Section heading, HELD from the full text. The page within R993-R1004 stays unresolved -- the publisher's HTML carries no page breaks, the same limitation as vreeman2007.", A_VALTIN, ["prepared_foods", "allowance_liters"], None, None),
        ("A.vreeman2007.c1", "vreeman2007", "§myth.1 (p. 1288)", "Page RESOLVED from the publisher PDF, which the PMC HTML could not give. Excerpt is the WEB edition. " + A_VREEMAN_PRINT_VARIANT, A_VREEMAN, ["prepared_foods"], "Heinz Valtin", None),
        ("A.valtin2002.q_stare", "valtin2002", "§POSSIBLE ORIGIN OF 8 × 8", "The block quotation, one paragraph below A.valtin2002.c1's passage. Same document, same section, different locus -- and classify_support must decline the pair on source_id alone.", A_VALTIN_STARE, ["stare_6to8", "stare_beverages"], "Frederick J. Stare and Margaret McWilliams", "Valtin names BOTH coauthors, in the text and again in his reasons against."),
        ("A.vreeman2007.q_stare", "vreeman2007", "§myth.1 (p. 1288)", "Excerpt is the WEB edition; the print drops 'once' and adds 'of'. Neither difference touches either span.", A_VREEMAN_STARE, ["stare_6to8", "stare_beverages"], "Frederick Stare", "The coauthor is GONE. Valtin's 'Drs. Stare and McWilliams' becomes 'a prominent nutritionist, Frederick Stare' -- a real attribution shift, five years and one hop downstream, and the second one slot A carries."),
        ("A.carroll2015.c1", "carroll2015", UNRESOLVED, "web article, no pagination", A_CARROLL, ["prepared_foods"], None, "Cited by hyperlink to Valtin's paper, never named in the body text. The field records what the document SAYS, and it says no name."),
    ],
    "assertions": [
        ("thomas_asserts_fnb_origin", "valtin2002", "fnb1945 -> the 8x8 claim", "Reported at TWO REMOVES and now fully cited: Valtin ref 65 is Papai J, 'Eight glasses of water per day. An update', urbanlegends.com, and Papai relays P. Thomas, who is never cited at all. Valtin states the mechanism -- the last sentence of the FNB passage 'was not heeded' -- which is why `thirst_qualifier` and `prepared_foods` matter. The downstream endpoint, the propagated claim, is ABSENT from this corpus, so the edge cannot form (A9). cited_by is EXPLICIT: the default -- every instance of the asserting document -- silently gave this assertion two endpoints once A.valtin2002.q_stare existed, both in valtin2002, so it formed no edge AND dropped out of unresolved_assertions. An assertion that vanishes is the precise failure A9 was written to prevent, and the default reintroduced it the moment a second locus was added.", ["A.valtin2002.c1"]),
        ("valtin_floats_stare_origin", "valtin2002", "stare1974 -> the 8x8 claim", "The RIVAL origin, and the one A10 said the corpus lacked. Valtin ref 81 is Stare FJ & McWilliams M, `Nutrition for Good Health`, Plycon, Fullerton CA, 1974, p. 175 -- reached not by search but through an OBITUARY (ref 77) and a former colleague (ref 82). Valtin quotes the passage in full, then gives four numbered reasons against it: undocumented, '6 to 8' is not 'at least eight', it ALLOWS caffeinated drinks, and it credits the regulation 8x8 denies. So the asserting document argues against its own assertion -- an edge no arm should draw with confidence. Upstream endpoint ABSENT: the Stare passage is RELAYED through Valtin, never HELD (A9).", ["A.valtin2002.q_stare"]),
        ("vc_asserts_fnb_origin", "vreeman2007", "fnb1945 -> the 8x8 claim", "'One origin may be a 1945 recommendation' (w5), with the mechanism at w6: 'If the last, crucial sentence is ignored...'. A SECOND document asserting the same undetermined edge, five years after Valtin, and hedged the same way. Downstream endpoint still absent (A9).", ["A.vreeman2007.c1"]),
        ("vc_asserts_stare_origin", "vreeman2007", "stare1974 -> the 8x8 claim", "'Another endorsement may have come from' (w7). Both investigators reached both candidates and neither picked one, which is the strongest evidence slot A has that the origin edge is genuinely undetermined rather than merely unresearched. Upstream endpoint absent (A9).", ["A.vreeman2007.q_stare"]),
    ],
    "known_gaps": [
        "Propagators: ROLE held from vreeman2007's body text ('found throughout the popular press.w1-w4') and CITATIONS held from Valtin's list (3 = UCLA S-N-A-C pamphlet 2000; 17 = Brody, NY Times, 11 July 2000, p. D8; 42 = Hines, Am Fitness 19:23-25, 2001; 54 = Majette-Haynes, IBWA). They are still NOT NODES: every propagator sentence available is relayed through Valtin, and only HELD is committable. The bmj.com w-list, which would give w1-w4's own identities, is behind a CAPTCHA and was not obtained.",
        "stare1974 itself not obtained. The rival origin now has textual substance -- two HELD documents quote it -- but the quoted document is absent, so both Stare assertions have an absent upstream endpoint.",
        "One locus is §unresolved (carroll2015, which has no pagination to resolve). fnb1945's page within pp. 3-18 and valtin2002's page within R993-R1004 are section-resolved only.",
        "thirst_qualifier is attested in one document and corroborated by nothing.",
        "vreeman2007 exists in TWO editions that differ inside slot A's own excerpts, and the corpus treats them as one source. Held as a decision, not an oversight: promoting the print run to its own source_id would add a fourth reading of the millilitre clause and a same-document pair the mechanism must decline. The key author owns that call, and carroll2015 has the identical fork.",
    ],
}

# =============================================================================
# SLOT B
# =============================================================================

B_G1956 = ("Einstein remarked to me many years ago that the cosmic repulsion idea was the "
           "biggest blunder he had made in his entire life.")
B_G1970 = ("Much later, when I was discussing cosmological problems with Einstein, he "
           "remarked that the introduction of the cosmological term was the biggest blunder "
           "he ever made in his life.")
B_WHEELER = ("Going into the doorway of the Institute for Advanced Study's Fuld Hall with "
             "Einstein and George Gamow, I heard Einstein say to Gamow about the cosmological "
             "constant, \"That was my biggest blunder of my life.\"")

SLOT_B: dict[str, Any] = {
    "slot": "B",
    "description": (
        "Slot B, suspension. PILOT. The Einstein nodes are not obtained, so every assertion "
        "of the attribution has an absent upstream endpoint and resolves as unreported edge "
        "plus recorded assertion (A9). The investigations (Livio, O'Raifeartaigh & Mitton) "
        "are not HELD by the worksheet author, so the disagreement A11 rests on is not yet "
        "IN the corpus -- only in the pre-registration."
    ),
    "sources": [
        ("gamow1956", "Gamow, George. \"The Evolutionary Universe.\" Scientific American 195, no. 3 (September 1956): 136-156.", "1956-09-01", "month", "origin of the attribution (A5)"),
        ("gamow1970", "Gamow, George. My World Line: An Informal Autobiography. New York: Viking Press, 1970, p. 44.", "1970-01-01", "year", "same author retelling, 14 years later"),
        ("wheeler2000", "Taylor, Edwin F., and John Archibald Wheeler. Exploring Black Holes: Introduction to General Relativity. San Francisco: Addison Wesley Longman, 2000.", "2000-01-01", "year", "second claimed eyewitness, admitted by A5"),
    ],
    "spans": [
        ("blunder_phrase", "was the biggest blunder he", ["gamow1956", "gamow1970"], "The longest verbatim run shared by the two Gamow tellings. wheeler2000 is DELIBERATELY ABSENT: it shares only 'biggest blunder', two tokens, which is the name of the legend. Recording that would produce a TEXTUAL edge contradicting Wheeler's own claim of independent hearing (A5)."),
    ],
    "instances": [
        ("B.gamow1956.c1", "gamow1956", UNRESOLVED, "page within pp. 136-156 not established; JSTOR access CAPTCHA'd", B_G1956, ["blunder_phrase"], "Albert Einstein", None),
        ("B.gamow1970.c1", "gamow1970", "§p44", None, B_G1970, ["blunder_phrase"], "Albert Einstein", None),
        ("B.wheeler2000.c1", "wheeler2000", "§pG-11", "Locus RELAYED from O'Raifeartaigh et al. 2017 fn. 48, which cites 'Taylor and Wheeler 2000 pG-11'. A pointer rather than an excerpt, so an error here surfaces on fetch. Which of the two named authors speaks in the first person is still unresolved.", B_WHEELER, [], "Albert Einstein", "Claimed FIRST-HAND, not via Gamow, while placing Gamow at the scene."),
    ],
    "assertions": [
        ("gamow1956_attributes_blunder_to_einstein", "gamow1956", "einstein -> the blunder phrase", "Gamow offers NO source. The upstream endpoint is not in the corpus, so the edge cannot form and the assertion is reported (A9)."),
        ("gamow1970_attributes_blunder_to_einstein", "gamow1970", "einstein -> the blunder phrase", "The same author asserting the same thing 14 years later, differently. Recorded separately because that is itself data."),
        ("wheeler_claims_direct_hearing", "wheeler2000", "einstein -> the blunder phrase, on independent first-hand authority", "An assertion of independent origin made 44 years after gamow1956 put the phrase in print. The mechanism cannot adjudicate it and must not try."),
    ],
    "known_gaps": [
        "einstein1917 and einstein1931 not obtained -- every attribution assertion therefore has an absent upstream endpoint.",
        "livio2013 and oraifeartaigh2018 not HELD by the author, so A11's investigator disagreement is not represented in the corpus.",
        "Segre, Folsing and Leahy -- the repeaters Livio names -- not obtained.",
        "gamow1956's page unresolved; wheeler2000's speaker unresolved.",
        "gamow1970's continuation, where Gamow puts 'blunder' in quotation marks, is not HELD and is omitted.",
    ],
}

# =============================================================================
# SLOT E
# =============================================================================

E_B1972 = "the fame of spinach may well have grown from a misplaced decimal point"
E_B1977 = "The fame of spinach appears to have been based on a misplaced decimal point"
E_HAMBLIN = ("German chemists reinvestigating the iron content of spinach had shown in the "
             "1930s that the original workers had put the decimal point in the wrong place "
             "and made a tenfold overestimate of its value.")

SLOT_E: dict[str, Any] = {
    "slot": "E",
    "description": (
        "Slot E, discrimination. PILOT, but the only slot whose CORE JOB IS ALREADY "
        "EXERCISED: it carries a TEXTUAL edge (bender1972 -> bender1977, a hedge erosion) and "
        "two TESTIMONY edges (bender* -> hamblin1981, asserted by Rekdal) in the same graph. "
        "That is exactly what `discrimination_correct` needs in order to be able to FAIL an "
        "arm that labels everything TESTIMONY. Note the shape: the endpoints of the testimony "
        "edges share only 'decimal point', two tokens, deliberately not recorded as a span -- "
        "so no textual reading competes with the testimony one, which is the clean case P2 "
        "registered. Still a pilot: three of five Bender nodes are missing, layer 1 is absent "
        "entirely, and no key exists."
    ),
    "sources": [
        ("bender1972", "Bender, Arnold E. The Wider Knowledge of Nutrition. Inaugural Lecture, 24 October 1972, Queen Elizabeth College, University of London. London: Castle Cary Press, 1972, p. 11.", "1972-10-24", "day", "origin of the decimal-point story (A12)"),
        ("bender1977", "Bender, Arnold E. \"Iron in spinach.\" The Spectator, 9 July 1977, p. 18.", "1977-07-09", "day", "same author, hedge weakened"),
        ("hamblin1981", "Hamblin, T. J. \"Fake!\" British Medical Journal 283, no. 6307 (19-26 December 1981): 1671-1674.", "1981-12-19", "day", "the assertion; names no source"),
        ("rekdal2014", "Rekdal, Ole Bjorn. \"Academic urban legends.\" Social Studies of Science 44, no. 4 (2014): 638-654. DOI 10.1177/0306312714535679. OnlineFirst 12 June 2014.", "2014-06-12", "day", "investigation; contributes the central testimony assertion WITHOUT a claim-instance of its own"),
    ],
    "spans": [
        ("fame_of_spinach", "fame of spinach", ["bender1972", "bender1977"], None),
        ("misplaced_decimal_point", "a misplaced decimal point", ["bender1972", "bender1977"], None),
    ],
    "instances": [
        ("E.bender1972.c1", "bender1972", "§p11", None, E_B1972, ["fame_of_spinach", "misplaced_decimal_point"], None, None),
        ("E.bender1977.c1", "bender1977", "§p18", None, E_B1977, ["fame_of_spinach", "misplaced_decimal_point"], None, None),
        ("E.hamblin1981.c1", "hamblin1981", "§p1671", "NARROWED to one continuous sentence. The worksheet excerpt carried ellipses and could not be hashed or diffed; the fuller passage remains un-obtained.", E_HAMBLIN, [], None, "Names NO ONE -- only 'German chemists' and 'the original workers'. Confirmed by a peer-reviewed source."),
    ],
    "assertions": [
        ("hamblin_asserts_decimal_origin", "hamblin1981", "an UNNAMED 19th-century analysis -> the iron-rich claim", "Hamblin gives no reference, no names, no dates. BOTH endpoints are absent from this corpus -- the upstream because he names none, the downstream because no layer-1 instance is obtained. The canonical A9 case.", ["E.hamblin1981.c1"]),
        ("rekdal_asserts_bender_to_hamblin", "rekdal2014", "bender1972/1977 -> hamblin1981", "THE CENTRAL TESTIMONY EDGE. Rekdal is a THIRD document, neither endpoint, so this resolves as TESTIMONY rather than textual -- which is correct, because the endpoints share only 'decimal point', two tokens, deliberately not recorded as a span. rekdal2014 contributes this record WITHOUT being a claim-instance: an assertion lives in the asserting document, and that document need not itself make a first-order claim in the corpus.", ["E.bender1972.c1", "E.bender1977.c1", "E.hamblin1981.c1"]),
    ],
    "known_gaps": [
        "bender1975a (p. 15), bender1975b (p. 142) and bender&bender1982 (p. 55) not obtained; the lineage is 2 of 5 nodes.",
        "bender&bender1982 missing means the SECOND undetermined edge -- the one Rekdal states himself -- cannot be built.",
        "sutton2010a and 2010b not obtained, so layer 3 has no dispute in the corpus.",
        "larsson1995 not obtained.",
        "No layer-1 instance, so Hamblin's assertion has no downstream endpoint and discrimination has no TEXTUAL half from layer 1 -- though the Bender span now supplies one.",
        "hamblin1981's excerpt is a narrowed continuous span, not the full passage.",
    ],
}


def build(spec: dict[str, Any]) -> dict[str, Any]:
    spans = spec["spans"]
    span_records: dict[str, list[str]] = {}
    evidence: list[dict[str, Any]] = []
    slot = spec["slot"]

    for span_id, text, appears, note in spans:
        ids = []
        for source_id in appears:
            record_id = f"ev_{slot}_{span_id}_{source_id}"
            ids.append(record_id)
            evidence.append({
                "evidence_id": record_id, "source_id": source_id, "span_id": span_id,
                "record_kind": "span", "summary": f"span '{span_id}' attested in {source_id}",
            })
        span_records[span_id] = ids

    # An assertion is cited by BOTH endpoints, and is located in the asserting
    # document -- which need not itself be a claim-instance. That is what lets
    # rekdal2014 supply slot E's central testimony edge without making a
    # first-order claim of its own.
    for assertion in spec["assertions"]:
        assertion_id, asserted_by, claims, note = assertion[:4]
        evidence.append({
            "evidence_id": f"ev_{slot}_assert_{assertion_id}", "source_id": asserted_by,
            "record_kind": "assertion", "claims": claims, "summary": note,
            "cited_by": list(assertion[4]) if len(assertion) > 4 else [],
        })

    instances = []
    for iid, source_id, locus, locus_note, excerpt, span_ids, attributed, note in spec["instances"]:
        cited = sorted({r for sid in span_ids for r in span_records[sid]})
        for assertion in spec["assertions"]:
            # Explicit `cited_by` names instances; absent it, the assertion is
            # cited by every instance of the document that made it.
            explicit = list(assertion[4]) if len(assertion) > 4 else None
            if (iid in explicit) if explicit is not None else (source_id == assertion[1]):
                cited.append(f"ev_{slot}_assert_{assertion[0]}")
        instances.append({
            "instance_id": iid, "source_id": source_id, "locus": locus, "locus_note": locus_note,
            "excerpt": excerpt, "excerpt_sha256": _sha(excerpt), "excerpt_status": "HELD",
            "attributed_to": attributed, "attribution_note": note,
            "belief_key": f"{slot.lower()}.inst.{iid.rsplit('.', 1)[-1]}.{source_id}",
            "proposition": f"[{source_id} {locus}] {excerpt}",
            "evidence_ids": sorted(set(cited)),
        })

    sources = []
    for source_id, citation, published, resolution, role in spec["sources"]:
        texts = sorted(i["excerpt"] for i in instances if i["source_id"] == source_id)
        sources.append({
            "source_id": source_id, "citation": citation, "published": published,
            "date_resolution": resolution, "role": role,
            "content_sha256": _sha("\n".join(texts)),
        })

    return {
        "fixture_id": f"corpus_{slot}", "role": "corpus", "slot": slot,
        "status": "PILOT - INCOMPLETE",
        "generated_by": "evals/analysis/exp08/build_corpora.py",
        "description": spec["description"],
        "sources": sources,
        "spans": [{"span_id": s, "text": t, "appears_in": a, "note": n} for s, t, a, n in spans],
        "asserted_descents": [
            {
                "assertion_id": a[0], "asserted_by": a[1], "claims": a[2], "note": a[3],
                "cited_by": list(a[4]) if len(a) > 4 else "all instances of the asserting document",
            }
            for a in spec["assertions"]
        ],
        "evidence": evidence,
        "claim_instances": instances,
        "key_authoring_note": {
            "rule": (
                "Record ONLY the highest-precedence mutation operator for each edge. An edge "
                "can genuinely carry several -- slot A has one that is both an attribution "
                "shift and a deletion -- but `mutation` is single-valued (A13), and a key "
                "recording both would count one as `misidentified` against an arm that was "
                "entirely correct."
            ),
            "precedence": [
                "attribution_shift -- attributed_to differs",
                "deletion -- the descendant's sentences are a proper subset of the ancestor's",
                "qualification -- the hedge set differs",
                "rewording -- the excerpts differ and nothing above applies",
                "none -- the excerpts are identical modulo whitespace and case",
            ],
            "pinned_by": "tests/test_exp08_properties.py::test_mutation_precedence_is_fixed",
        },
        "expect": {
            "instance_count": len(instances), "source_count": len(sources),
            "span_count": len(spans), "assertion_count": len(spec["assertions"]),
            "note": (
                "Structural only. No expected edge, support kind or mutation appears here -- "
                f"those live in key_{slot}.json, authored by hand and separately (FR-2)."
            ),
        },
        "known_gaps": spec["known_gaps"],
    }


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for spec in (SLOT_A, SLOT_B, SLOT_E):
        corpus = build(spec)
        path = FIXTURES / f"corpus_{spec['slot']}.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(corpus, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print(f"  {path.name}: {len(corpus['claim_instances'])} instances, "
              f"{len(corpus['sources'])} sources, {len(corpus['spans'])} spans, "
              f"{len(corpus['asserted_descents'])} assertions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
