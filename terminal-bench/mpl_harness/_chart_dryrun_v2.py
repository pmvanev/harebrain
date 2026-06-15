"""Stub-host dry-run of terminal_v2.mpl -- no Docker, no LLM, no API spend.

Proves the three things the v2 walking skeleton claims (the constructs the spike
unblocked), end to end through the live mplv2 engine:

  A) verify PASS              -> the cage reaches Done
  B) verify FAILs then PASSes -> the gate loops back to Perceive, then reaches
                                 Done (verify_fails == 1) -- "premature done" is
                                 structurally blocked
  C) verify ALWAYS fails      -> bounded retries (verify_fails == max), then SUBMIT
                                 (Done) so a wrong/over-strict predicate never traps
                                 a correct solution (see check-soundness.md)
  D) solver NEVER claims done -> the @priority(100) multi-source budget rule is the
                                 outer backstop and HALTS in Abort at steps == max

Run via the WSL tool-venv python (which has mpl):
  /root/.local/share/uv/tools/terminal-bench/bin/python _chart_dryrun_v2.py
"""

from pathlib import Path

import mpl

CHART = str(Path(__file__).parent / "terminal_v2.mpl")
DONE = "__DONE__"


def safe(sim, path):
    try:
        return sim[path]
    except Exception as e:
        return f"<{type(e).__name__}>"


def run(name, decide_script, check_script, max_ticks=200):
    """decide_script: commands returned by decide() in order, then the last repeats.
    check_script: bools returned by check() in order, then the last repeats."""
    sim = mpl.Simulation(mpl.load(CHART), seed=0)
    mod = mpl.HostModule("agent")
    st = {"d": 0, "c": 0}

    @mod.export
    def observe() -> str:
        return "fake screen"

    @mod.export
    def decide(obs: str) -> str:
        i = st["d"]
        st["d"] += 1
        return decide_script[i] if i < len(decide_script) else decide_script[-1]

    @mod.export
    def act(command: str) -> str:
        return "screen after " + command

    @mod.export
    def check() -> bool:
        i = st["c"]
        st["c"] += 1
        return check_script[i] if i < len(check_script) else check_script[-1]

    sim.register_host(mod)
    sim.validate_hosts()

    end = None
    for _ in range(max_ticks):
        if not getattr(sim, "running", True):
            break
        try:
            sim.tick(0.1)
        except mpl.SimulationStopped:
            break
        if safe(sim, "Agent/Done") is True:
            end = "Done"
            break
        if safe(sim, "Agent/Abort") is True:
            end = "Abort"
            break

    vf = safe(sim, "Agent/verify_fails")
    print(
        f"[{name}] end={end} steps={safe(sim,'Agent/steps')} "
        f"verify_fails={vf} decide_calls={st['d']} check_calls={st['c']}"
    )
    return end, vf


def main():
    print("compiled OK:", mpl.load(CHART) is not None)
    ok = True

    end, _ = run("A verify-pass", ["echo hi", "ls", DONE], [True])
    ok &= end == "Done"

    end, vf = run("B fail-then-pass", [DONE], [False, True])
    ok &= end == "Done" and vf == 1

    # always-fail: bounded retries then SUBMIT (defer to the grader), not a false Abort
    end, vf = run("C always-fail -> submit", [DONE], [False])
    ok &= end == "Done" and vf == 2

    # never-done solver: only the @priority budget rule can stop it -> Abort
    end, _ = run("D never-done -> HALT", ["echo loop"], [True])
    ok &= end == "Abort"

    print("\nWALKING SKELETON WIRING:", "OK" if ok else "BROKEN")


if __name__ == "__main__":
    main()
