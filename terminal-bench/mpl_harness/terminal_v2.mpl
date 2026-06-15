// Terminal-Bench agent as an MPL cage -- v2 WALKING SKELETON.
//
// Built incrementally from v1 (../agents/terminal.mpl). It adds ONLY the two
// constructs the SPIKE validated against the live mplv2 package
// (see spike-findings.md) -- nothing speculative:
//
//   1. A SOUND VERIFY GATE. When the brain claims done, the cage does NOT
//      terminate on that claim. It enters Verify, runs check() once (a
//      host-side sound check of the task's observable end-state), and reaches
//      Done only if the check agrees. A failed check loops back to Perceive,
//      so "premature done" is structurally unreachable (design section 1, the
//      accuracy-first lever). [validated: write-in-then / read-next-tick]
//
//   2. A @priority ABORT guard. One high-priority multi-source rule preempts
//      every normal transition the instant steps >= max_steps, guaranteeing the
//      cage HALTS (design section 3). [validated: @priority wins the tick;
//      multi-source S1|S2|... form per stopwatch.mpl]
//
// DELIBERATELY OMITTED: the section-6 stochastic action-selection region. The
// spike showed choose(1){@weight} is NOT a seeded random draw (deterministic,
// weight- and seed-independent), so that region waits on a host-seeded rand01()
// import. This skeleton stays fully deterministic-given-seed.
//
// Host leaves (v1's three, plus check):
//   observe()    -> current terminal screen
//   decide(obs)  -> next shell command, or "__DONE__" when the brain is done
//   act(command) -> run command, return new screen
//   check()      -> True iff the task's observable end-state verifies (SOUND).
//                   NOTE: check() soundness (re-running visible checks without
//                   leaking the hidden grader) is still an OPEN design question
//                   (Risk #1). The skeleton wires the gate; the host supplies a
//                   placeholder check until soundness is resolved.

host import {
    observe() -> string,
    decide(obs:string) -> string,
    act(command:string) -> string,
    check() -> bool,
} from agent;

default machine Agent {
    vars {
        obs:string := "";
        cmd:string := "";
        last_screen:string := "";
        steps:int := 0;
        max_steps:int := 30;
        verify_fails:int := 0;
        max_verify_fails:int := 2;
        verified:bool := false;
        finished:bool := false;
    }

    state Perceive;
    state Think;
    state Act;
    state Verify;
    state Checked;
    state Done;
    state Abort;
    ENTER => Perceive;

    // --- Budget HALT: a single @priority rule preempts every normal
    //     transition the moment the step budget is spent. Done/Abort are
    //     terminal and intentionally excluded. ---
    @priority(100) Perceive | Think | Act | Verify | Checked
        when steps >= max_steps => Abort then { finished := true; };

    // --- perceive -> think -> act loop (unchanged from v1) ---
    Perceive => Think then { obs := observe(); };
    Think => Act then { cmd := decide(obs); steps += 1; };

    // Brain claims done: do NOT terminate -- enter the verify gate.
    Act when cmd == "__DONE__" => Verify;
    // Otherwise run one command and loop.
    Act when cmd != "__DONE__" => Perceive then { last_screen := act(cmd); };

    // --- Sound verify gate (run check() once, then branch on the result) ---
    // check() is a SOUND lower bound, not the hidden oracle (see check-soundness.md):
    // a deterministic predicate over the real end-state, derived from the public
    // instruction by a separate verifier pass. A FAIL is a real observable deficiency;
    // a PASS is necessary-not-sufficient. The loop is BOUNDED and defers to the real
    // grader on exhaustion -- a wrong/over-strict predicate must never trap an actually
    // correct solution and burn the budget into a false Abort.
    Verify => Checked then { verified := check(); };
    Checked when verified => Done then { finished := true; };
    // Failed but retries remain: count it and go back to work.
    Checked when !verified && verify_fails < max_verify_fails => Perceive then { verify_fails += 1; };
    // Retries exhausted: SUBMIT anyway and let the sound external grader adjudicate.
    Checked when !verified && verify_fails >= max_verify_fails => Done then { finished := true; };

    // Done and Abort are terminal (no outgoing rules).
}
