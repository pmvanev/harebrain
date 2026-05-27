Feature: R4 variant + surface — configurable engine, Mystery seam

  As harness-harriet
  I want to vary Yob's parameters via configuration without touching engine code
  So that the escalation ladder and variant experiments ship as configs, not forks.

  Scenario: VariantConfig() yields Yob 1973 defaults
    Given a VariantConfig constructed with no arguments
    Then room_count is 20, wumpus_count is 1, pit_count is 2, bat_count is 2
    And arrow_count is 5, arrow_max_range is 5, wumpus_move_prob is 0.75
    And escalation_rules is empty

  Scenario: arrow_count variant changes the out-of-arrows terminal
    Given Game(seed=42, variant=VariantConfig(arrow_count=3))
    When the player misses three times
    Then GameEnded(outcome=out_of_arrows) fires after the third miss
    And the same scenario with default arrow_count=5 does NOT end after three misses

  Scenario: VariantConfig is recorded structurally in GameStarted
    Given Game(seed=42, variant=VariantConfig(arrow_count=3)) with a JsonlSink
    When the first ledger line is read
    Then GameStarted.variant_config contains arrow_count=3 and room_count=20

  Scenario: Variants do not change the internal state schema
    Given Game(seed=42, variant=VariantConfig(wumpus_count=2))
    When game.snapshot() is taken
    Then snap.world.wumpus_rooms has length 2
    And the snapshot's field set is identical to a wumpus_count=1 snapshot's field set

  # ---- R4-S02 — escalation_rules extension point ----

  Scenario: IdentityRule is byte-identical to no-rules
    Given two Games on the same seed and action sequence, one with escalation_rules=() and one with escalation_rules=(IdentityRule(),)
    When both are driven through the identical action sequence
    Then their emitted event sequences are byte-identical
    And their rendered output is byte-identical

  Scenario: EscalationRule is a Protocol with named hook methods
    Given the wumpus.types.EscalationRule type
    Then it is a typing.Protocol
    And IdentityRule structurally satisfies it with name, filter_observation, and filter_events

  Scenario: Multiple rules are consulted left-to-right and the order survives snapshot round-trip
    Given Game(seed=42, variant=VariantConfig(escalation_rules=(RuleA(), RuleB())))
    When the engine consults the rules at an event-emission decision point
    Then RuleA is consulted before RuleB
    And active_escalation_rules records ("a", "b") in order
    And the order is preserved across a snapshot round-trip
