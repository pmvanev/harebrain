Feature: R4 surface seam — Surface Protocol + YobSurface

  As harness-harriet running Mystery probes (and as the engine maintainer)
  I want all surface-form strings consolidated behind a clean Surface interface
  So that the seam claim (SC8) is achievable and a non-Yob surface is implementable.

  # ---- R4-S03 — Surface interface + YobSurface ----

  # AC scenario 1 is REDEFINED per ADR-011 (Determinism Decision): the 10 BASIC
  # byte-parity fixtures do not exist and never will (the engine uses Python
  # random.Random, PC-BASIC uses GW-BASIC RND). The safety net that the surface
  # refactor did not change Yob output is the R1 yob-fidelity acceptance suite
  # (it exercises the real Yob prompts/strings/messages) plus the determinism
  # golden master. Both MUST stay green after the refactor.
  Scenario: The Yob-fidelity regression net survives the surface refactor
    Given the surface refactor has landed (Surface Protocol + YobSurface)
    When the R1 yob-fidelity acceptance suite and the determinism golden master are re-run
    Then both suites pass without modification
    And YobSurface still emits every canonical Yob string byte-for-byte

  Scenario: Surface interface covers every surface-form string the engine emits
    Given a YobSurface instance bound to the Surface Protocol
    Then it exposes room_label, sense_string, hazard_name, command_token, command_parse, prompt_text, and instructions_block
    And every prompt the engine awaits has a non-empty prompt_text rendering
    And every sense and hazard kind the engine emits has a non-empty surface rendering

  Scenario: Surface command translation round-trips for every verb
    Given a YobSurface instance bound to the Surface Protocol
    When command_parse(command_token(verb)) is invoked for every CommandVerb
    Then the result equals the original verb
