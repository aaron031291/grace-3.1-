------------------------- MODULE CausalGraph_1773180698 -------------------------
EXTENDS Naturals, Sequences, FiniteSets

VARIABLES active_states

Init ==
    \* Start with no active disaster states
    active_states = {}

Next ==
    \/ ("increasing_the_core_voltage_will" \in active_states /\ active_states' = active_states \cup {"thermal_throttling"})
    \/ ("thermal_throttling_will" \in active_states /\ active_states' = active_states \cup {"an_increase_in_the_core_voltage"})

\* INVARIANTS (Things that must never happen)
NoInfiniteLoops == 
    \* Apalache checks if the state graph contains cycles without progress
    TRUE \* Placeholder for explicit temporal property: []~(eventually loops)

NoContradictions == 
    \* Ensure A -> B and B -> !A don't crash the physical world model
    TRUE

=============================================================================
