"""MPL-cage Terminal-Bench agent, v2 -- adds the SOUND verify gate.

Control flow is terminal_v2.mpl (this dir). On top of v1's perceive->think->act
loop it adds a verify gate and a @priority budget HALT (both spike-validated).
This host wires the chart's four `host import` leaves:

    observe()    -> session.capture_pane()            (the cage's eyes)
    decide(obs)  -> one SOLVER LLM call -> a command   (the brain, at a leaf)
    act(command) -> session.send_keys(...)             (the cage's hands)
    check()      -> one VERIFIER LLM call -> a bash predicate, run for its exit
                    code against the REAL end-state    (the sound gate)

check() is the design in check-soundness.md: a SEPARATE verifier pass (decorrelated
from the solver) re-derives the task's observable success condition from the PUBLIC
instruction and asserts it deterministically. It never reads the hidden grader
($TEST_DIR / tests/) -- which isn't in the container during the run anyway.

Run (from a uv env that has BOTH terminal-bench and mpl), e.g.:

    PYTHONPATH=/mnt/c/.../terminal-bench/mpl_harness \
      tb run --agent-import-path mpl_agent_v2:MplAgentV2 \
        -m gemini/gemini-2.5-flash -t hello-world -d terminal-bench-core==0.1.1 \
        --output-path ~/tb-runs
"""

import re
from pathlib import Path

import mpl
from pydantic import BaseModel, Field

from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.lite_llm import LiteLLM
from terminal_bench.terminal.tmux_session import TmuxSession

DONE_SENTINEL = "__DONE__"
CHECK_MARKER = "MPLCHKEXIT"


class Decision(BaseModel):
    command: str = Field(description="One shell command to run next (ignored if done)")
    done: bool = Field(description="True when the task is fully complete")


class Verification(BaseModel):
    predicate: str = Field(
        description="A single bash command line that exits 0 iff the task's stated "
        "requirements are demonstrably met by the current filesystem state"
    )


class MplAgentV2(BaseAgent):
    def __init__(
        self,
        model_name: str,
        chart: str | None = None,
        verifier_model_name: str | None = None,
        max_ticks: int = 200,
        gate: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._llm = LiteLLM(model_name=model_name)
        # Verifier defaults to the same model; can be split for true decorrelation.
        self._verifier = LiteLLM(model_name=verifier_model_name or model_name)
        self._chart = chart or str(Path(__file__).parent / "terminal_v2.mpl")
        self._max_ticks = int(max_ticks)
        # gate=False is the ablation: the verify gate becomes a no-op (the done-claim
        # is accepted immediately), isolating the gate's contribution vs the same
        # cage/model/budget. See MplAgentV2NoGate.
        self._gate = bool(gate)

    @staticmethod
    def name() -> str:
        return "mpl-terminal-v2"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        # Token accounting: solver and verifier tracked separately, summed for the
        # reported totals so the gate's cost shows up honestly (priority #2).
        c = {
            "sin": 0, "sout": 0, "vin": 0, "vout": 0,
            "parse_failed": False, "checks": 0,
            "consec_errs": 0, "host_dead": False,
        }

        def _note_err():
            # Container death / repeated host-call failure -> stop ticking a dead
            # session (the pilot showed ~120 wasted ticks flooding 404s otherwise).
            c["consec_errs"] += 1
            if c["consec_errs"] >= 3:
                c["host_dead"] = True

        agent_mod = mpl.HostModule("agent")

        @agent_mod.export
        def observe() -> str:
            try:
                s = session.capture_pane()
                c["consec_errs"] = 0
                return s
            except Exception:
                _note_err()
                return ""

        @agent_mod.export
        def decide(obs: str) -> str:
            prompt = (
                "You are operating a Linux terminal to complete a task. Work one "
                "shell command at a time.\n\n"
                f"TASK:\n{instruction}\n\n"
                f"CURRENT SCREEN:\n{obs}\n\n"
                'Reply as JSON: {"command": "<the single next shell command to run '
                'now>", "done": <true once the task is complete>}. Always include the '
                "command if any work remains — even if it is the last step. Leave "
                '"command" as an empty string ONLY when the task is already fully '
                "complete and nothing remains to run."
            )
            raw = self._llm.call(prompt, response_format=Decision)
            c["sin"] += self._llm.count_tokens([{"role": "user", "content": prompt}])
            c["sout"] += self._llm.count_tokens([{"role": "assistant", "content": raw}])
            try:
                d = Decision.model_validate_json(raw)
            except Exception:
                c["parse_failed"] = True
                return DONE_SENTINEL
            cmd = (d.command or "").strip()
            return cmd if cmd else DONE_SENTINEL

        @agent_mod.export
        def act(command: str) -> str:
            try:
                session.send_keys([command, "Enter"], block=True)
                s = session.capture_pane()
                c["consec_errs"] = 0
                return s
            except Exception:
                _note_err()
                return ""

        @agent_mod.export
        def check() -> bool:
            # SOUND verify gate: a separate verifier authors a deterministic predicate
            # from the PUBLIC instruction + observed state; we run it for its exit code.
            if not self._gate:
                return True  # ablation: gate off -> accept the done-claim immediately
            c["checks"] += 1
            screen = session.capture_pane()
            prompt = (
                "You are a STRICT, INDEPENDENT verifier — separate from the agent that "
                "did the work. Decide whether the task's requirements are DEMONSTRABLY "
                "satisfied by the CURRENT terminal/filesystem state.\n\n"
                "Output a single bash command line (a predicate) that exits 0 if and "
                "only if every stated requirement is met, and non-zero otherwise.\n"
                "Rules:\n"
                "- Assert ONLY what the task explicitly requires; do not invent "
                "requirements.\n"
                "- Inspect the REAL current state (files, contents, permissions, "
                "command output).\n"
                "- Do NOT read or reference any test files, a tests/ directory, "
                "$TEST_DIR, or any solution file — verify from the task text alone.\n"
                "- Output ONLY the predicate in the JSON field, no prose, no markdown.\n\n"
                f"TASK:\n{instruction}\n\n"
                f"CURRENT SCREEN:\n{screen}\n"
            )
            try:
                raw = self._verifier.call(prompt, response_format=Verification)
                c["vin"] += self._verifier.count_tokens(
                    [{"role": "user", "content": prompt}]
                )
                c["vout"] += self._verifier.count_tokens(
                    [{"role": "assistant", "content": raw}]
                )
                predicate = Verification.model_validate_json(raw).predicate.strip()
            except Exception:
                # A broken verifier is NOT a pass; bounded retries then submit (chart).
                return False
            if not predicate:
                return False
            # Run the predicate and read its exit code via a marker echo.
            try:
                session.send_keys(
                    [f"{predicate}; echo {CHECK_MARKER}=$?", "Enter"], block=True
                )
                out = session.capture_pane()
                c["consec_errs"] = 0
            except Exception:
                _note_err()
                return False
            hits = re.findall(rf"{CHECK_MARKER}=(\d+)", out)
            return bool(hits) and hits[-1] == "0"

        model = mpl.load(self._chart)
        sim = mpl.Simulation(model, seed=0)
        sim.register_host(agent_mod)
        sim.validate_hosts()

        for _ in range(self._max_ticks):
            if not getattr(sim, "running", True) or c["host_dead"]:
                break
            try:
                sim.tick(0.1)
            except mpl.SimulationStopped:
                break
            if c["host_dead"]:
                break
            try:
                if sim["Agent/finished"]:
                    break
            except Exception:
                pass

        if logging_dir is not None:
            try:
                (logging_dir / "mpl_v2_metrics.txt").write_text(
                    f"solver_in={c['sin']} solver_out={c['sout']} "
                    f"verifier_in={c['vin']} verifier_out={c['vout']} "
                    f"checks={c['checks']}\n"
                )
            except Exception:
                pass

        return AgentResult(
            total_input_tokens=c["sin"] + c["vin"],
            total_output_tokens=c["sout"] + c["vout"],
            failure_mode=(
                FailureMode.FATAL_LLM_PARSE_ERROR
                if c["parse_failed"]
                else FailureMode.NONE
            ),
        )


class MplAgentV2NoGate(MplAgentV2):
    """Ablation of MplAgentV2: the verify gate is a no-op (the brain's done-claim is
    accepted immediately, like v1). Same chart, model, and step budget — the ONLY
    difference is whether check() actually verifies. Run this alongside MplAgentV2 on
    the same tasks to attribute the sound gate's contribution to accuracy (design §8)."""

    def __init__(self, *args, **kwargs):
        kwargs["gate"] = False
        super().__init__(*args, **kwargs)

    @staticmethod
    def name() -> str:
        return "mpl-terminal-v2-nogate"
