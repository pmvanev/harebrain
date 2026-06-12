"""Standalone dry-run of terminal.mpl with stub host functions.

Validates that the chart compiles, the host-import contract matches, and the
perceive->think->act loop progresses and terminates -- without Docker or any LLM.
"""

from pathlib import Path

import mpl

chart = str(Path(__file__).parent / "terminal.mpl")


def safe(sim, path):
    try:
        return sim[path]
    except Exception as e:
        return f"<{type(e).__name__}>"


def main():
    model = mpl.load(chart)
    print("compiled OK")
    sim = mpl.Simulation(model, seed=0)

    mod = mpl.HostModule("agent")
    state = {"calls": 0}

    @mod.export
    def observe() -> str:
        return "fake screen contents"

    @mod.export
    def decide(obs: str) -> str:
        state["calls"] += 1
        return "echo hi" if state["calls"] < 2 else "__DONE__"

    @mod.export
    def act(command: str) -> str:
        print("   ACT:", command)
        return "screen after"

    sim.register_host(mod)
    sim.validate_hosts()
    print("hosts validated OK")

    for i in range(40):
        if not getattr(sim, "running", True):
            print("sim not running; stop")
            break
        sim.tick(0.1)
        fin = safe(sim, "Agent/finished")
        print(
            f"tick {i:2d}: finished={fin} steps={safe(sim,'Agent/steps')} "
            f"cmd={safe(sim,'Agent/cmd')!r} "
            f"P={safe(sim,'Agent/Perceive')} T={safe(sim,'Agent/Think')} "
            f"A={safe(sim,'Agent/Act')} D={safe(sim,'Agent/Done')}"
        )
        if fin is True:
            print(f"FINISHED at tick {i}, decide calls={state['calls']}")
            break


if __name__ == "__main__":
    main()
