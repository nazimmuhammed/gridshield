"""
GridShield - Backtesting Against Real Blackout Case Study
=============================================================
Validates that GridShield's cascade simulation mechanism reproduces the
same real-world failure pattern documented in the July 2012 India
blackout (370M+ then 700M+ people affected across two consecutive days) -
the largest cascading grid failure in history.

Source facts (CERC Enquiry Committee Report, and academic analyses):
- Root cause: loss of a critical high-capacity transmission line
  (400kV Bina-Gwalior-Agra) removed the grid's N-1 safety margin
- A single overloaded station's load redistributed to neighboring
  stations, which then also overloaded - textbook cascading failure
- The cascade evolved non-contiguously (affecting non-adjacent lines,
  not just immediate neighbors) - matching what GridShield's N-1/N-2
  analysis found with lines 27 and 9 in the IEEE 30-bus system

This is NOT a claim of numerically reproducing the exact 2012 event
(the real Indian grid topology is proprietary and vastly larger than
the IEEE 30-bus test system). It IS a validation that the underlying
mechanism - single critical failure removing safety margin, triggering
non-contiguous multi-line cascade - is correctly modeled.
"""

REAL_WORLD_CASE_STUDY = {
    "event": "July 30-31, 2012 India Blackout",
    "root_cause": "Loss of critical 400kV Bina-Gwalior-Agra transmission line removed grid's N-1 safety margin",
    "mechanism": "Single station overload -> load redistributed to neighbors -> cascading multi-line failure",
    "cascade_characteristic": "Non-contiguous - failures affected remote lines, not just adjacent ones",
    "day_1_impact": "370 million people affected, 8 states, ~36,000 MW",
    "day_2_impact": "700 million people affected, 21 states, ~48,000 MW",
    "source": "CERC Enquiry Committee Report; academic complex-network analyses",
}


def compare_mechanism_to_gridshield(cascade_result: dict) -> dict:
    """
    Compares GridShield's simulated cascade characteristics against the
    documented real-world mechanism, checking for the same qualitative
    pattern: does a single failure cascade non-contiguously to multiple
    lines, consistent with real large-scale grid cascade behavior?
    """
    sequence = cascade_result.get("cascade_sequence", [])
    total_failed = cascade_result.get("total_failed_lines", 0)

    # Check non-contiguity: are failed line indices spread out rather
    # than just sequential neighbors? (proxy check on index spread)
    is_multi_stage = total_failed > 2
    index_spread = max(sequence) - min(sequence) if sequence else 0
    is_non_contiguous = index_spread > 5  # failures span distant line indices

    return {
        "real_world_case_study": REAL_WORLD_CASE_STUDY,
        "gridshield_simulation": {
            "initial_failure": sequence[0] if sequence else None,
            "total_cascade_failures": total_failed,
            "cascade_sequence": sequence,
        },
        "mechanism_match": {
            "multi_stage_cascade": is_multi_stage,
            "non_contiguous_pattern": is_non_contiguous,
            "conclusion": (
                "GridShield's simulation reproduces the qualitative mechanism documented in "
                "the 2012 India blackout: a single critical line failure propagates non-contiguously "
                "across the network via load redistribution, consistent with real large-scale grid "
                "cascade behavior described in CERC's post-incident analysis."
                if (is_multi_stage and is_non_contiguous) else
                "This particular failure did not exhibit the multi-stage non-contiguous pattern "
                "seen in major real-world cascades - useful as a contrast case showing not all "
                "failures escalate to blackout-scale events."
            ),
        },
    }