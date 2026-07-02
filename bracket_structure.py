# Static top-to-bottom slot order for the knockout bracket tree, keyed by
# football-data.org api_id. Match kickoff order (used elsewhere in the app)
# is chronological, NOT bracket position, so it can't drive a real bracket
# visual — this table is what lets the /bracket UI nest each round's matches
# under the correct pair from the round before it.
#
# Order derived from FIFA's official match-number wiring (M73-M104):
#   R16  M89=W(M73,M74)  M90=W(M75,M76)  M91=W(M79,M80)  M92=W(M81,M82)
#        M93=W(M77,M78)  M94=W(M83,M84)  M95=W(M85,M86)  M96=W(M87,M88)
#   QF   M97=W(M89,M90)  M98=W(M93,M94)  M99=W(M91,M92)  M100=W(M95,M96)
#   SF   M101=W(M97,M98) M102=W(M99,M100)
#   3rd  M103=Loser(M101,M102)   Final  M104=W(M101,M102)
# The api_id <-> M-number mapping for Round of 32 matches the match-number
# comments already in bracket_labels.py.
#
# Round of 16 / QF / SF order below was cross-checked against this app's own
# kickoff timestamps (dates/times line up exactly, in a non-chronological
# sequence that only makes sense as bracket-tree order) rather than derived
# from FIFA match numbers directly, since those aren't recorded anywhere.
BRACKET_ORDER = {
    'LAST_32': [
        537417, 537415, 537418, 537423,
        537416, 537424, 537419, 537420,
        537425, 537426, 537421, 537422,
        537429, 537427, 537430, 537428,
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
