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

  # ---- R4-S05 — obfuscation-gap measurement (journey J2) ----
  #
  # The surface seam is STRUCTURAL, not cosmetic: a MysterySurface and the
  # default YobSurface, run from the SAME seed with translation-equivalent
  # actions, produce an IDENTICAL internal trajectory — equal internal_state_hash
  # at every turn. Only the bytes the player reads differ. That equality is the
  # validity proof of the obfuscation-gap measurement (SC8/SC9).

  # Framed as invariant properties (the PBT mandate); expressed via the
  # `Scenario:` keyword because this repo's Gherkin parser (official grammar)
  # does not accept a `Property:` keyword. The broad equivalence-class coverage
  # lives in tests/property/test_obfuscation_gap.py; these pin the canonical
  # walkthrough.

  Scenario: Paired classic and mystery runs produce identical internal trajectories
    Given the same seed and a sequence of internal action intents
    When the engine is driven once via the Yob surface and once via the Mystery surface with translation-equivalent inputs
    Then the emitted internal_state_hash sequence is identical at every turn

  Scenario: Mystery surface does not consume engine RNG
    Given the same seed and a sequence of internal action intents
    When the engine is driven once via the Yob surface and once via the Mystery surface with translation-equivalent inputs
    Then the emitted rng_cursor sequence is identical at every turn

  Scenario: Mystery surface genuinely obfuscates the rendered bytes
    Given the same seed and a sequence of internal action intents
    When the engine is driven once via the Yob surface and once via the Mystery surface with translation-equivalent inputs
    Then the rendered player-visible output of the Mystery run differs from the Yob run

  # ---- R4-S06 — surface-generality smoke (FrenchSurface drops in, no engine changes) ----
  #
  # R4-S05 proved the surface seam works for ONE non-Yob surface (Mystery). The
  # risk it leaves open: was that seam Mystery-shaped? R4-S06 falsifies that risk
  # by dropping in a SECOND, independent, non-Mystery surface (FrenchSurface, a
  # real-language translation) and showing the SAME structural equality holds —
  # with NO engine changes. If French needed an engine edit, the seam would have
  # been Mystery-specific. Same invariant-property framing as R4-S05 (the repo's
  # Gherkin parser does not accept a `Property:` keyword); the broad
  # equivalence-class coverage lives in tests/property/test_obfuscation_gap.py
  # (now parametrized over Mystery AND French), these pin the canonical example.

  Scenario: FrenchSurface reports its variant in the GameStarted header
    Given a Game driven via the French surface
    Then the GameStarted header records surface_id "french"

  Scenario: Paired classic and French runs produce identical internal trajectories
    Given the same seed and a sequence of internal action intents
    When the engine is driven once via the Yob surface and once via the French surface with translation-equivalent inputs
    Then the Yob and French internal_state_hash sequence is identical at every turn
    And the Yob and French rng_cursor sequence is identical at every turn

  Scenario: French surface genuinely translates the rendered bytes
    Given the same seed and a sequence of internal action intents
    When the engine is driven once via the Yob surface and once via the French surface with translation-equivalent inputs
    Then the rendered player-visible output of the French run differs from the Yob run
