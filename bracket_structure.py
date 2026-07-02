# Static top-to-bottom slot order for the knockout bracket tree, keyed by
# football-data.org api_id. Match kickoff order (used elsewhere in the app)
# is chronological, NOT bracket position, so it can't drive a real bracket
# visual — this table is what lets the /bracket UI nest each round's matches
# under the correct pair from the round before it.
#
# Round of 32 order: an earlier version of this table was built from a
# FIFA match-number wiring (M73-M104) sourced via web lookup, which turned
# out to be wrong for this competition's actual api_ids. It's since been
# rebuilt from ground truth: once the first 10 Round of 32 matches had real
# results, every one of them showed the SAME simple rule — feeder pairs are
# just consecutive api_ids (537415+537416, 537417+537418, 537419+537420, ...).
# e.g. 537417 (SA v Canada) and 537418 (Netherlands v Morocco) both feed
# 537376 (Canada v Morocco) in Round of 16 — confirmed against real results.
# The remaining 3 pairs (537419/420, 537427/428, 537429/430, all still
# unplayed) are placed by matching their kickoff order to the Round of 16
# slot order below; revisit once those Round of 32 matches finish.
#
# Round of 16 / QF / SF order was cross-checked against this app's own
# kickoff timestamps (dates/times line up exactly, in a non-chronological
# sequence that only makes sense as bracket-tree order).
BRACKET_ORDER = {
    'LAST_32': [
        537417, 537418, 537415, 537416,
        537421, 537422, 537419, 537420,
        537423, 537424, 537425, 537426,
        537429, 537430, 537427, 537428,
    ],
    'LAST_16': [537376, 537375, 537380, 537379, 537377, 537378, 537382, 537381],
    'QUARTER_FINALS': [537383, 537384, 537385, 537386],
    'SEMI_FINALS': [537387, 537388],
    'FINAL': [537390],
    'THIRD_PLACE': [537389],
}

# Stages that form the connected "path to the final" tree (excludes THIRD_PLACE,
# which is fed by the two semi-final losers rather than sitting in the winners' tree).
BRACKET_MAIN_STAGES = ['LAST_32', 'LAST_16', 'QUARTER_FINALS', 'SEMI_FINALS', 'FINAL']


def slot_positions(count):
    """Evenly-spaced vertical center points (as % of column height) for `count`
    items, chosen so that adjacent pairs at one round average out exactly to a
    slot's position in the next (halved) round — i.e. connector lines meet up."""
    if count <= 0:
        return []
    return [round((2 * i + 1) / (2 * count) * 100, 4) for i in range(count)]
