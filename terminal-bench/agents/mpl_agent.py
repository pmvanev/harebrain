"""A custom Terminal-Bench agent whose control flow is an MPL chart (the harebrain cage).

The chart (`terminal.mpl`) owns the perceive->think->act loop, the step budget, and
termination. This host wires the chart's three `host import` leaves to the live task:

    observe()      -> session.capture_pane()          (the cage's eyes)
    decide(obs)    -> one LLM call, returns a command  (the brain, at a leaf)
    act(command)   -> session.send_keys(...)           (the cage's hands)

This is the harebrain hypothesis as an experiment: same model, a structured game-AI
cage, measured on the Terminal-Bench ruler. See ../custom-agents.md.

Run (from a uv env that has BOTH terminal-bench and mpl):

    PYTHONPATH=/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain/terminal-bench/agents \
      tb run --agent-import-path mpl_agent:MplAgent \
        -m gemini/gemini-2.5-flash -t hello-world -d terminal-bench-core==0.1.1 \
        --output-path ~/tb-runs
"""

from pathlib import Path

import mpl
from pydantic import BaseModel, Field

from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.lite_llm import LiteLLM
from terminal_bench.terminal.tmux_session import TmuxSession

DONE_SENTINEL = "__DONE__"


class Decision(BaseModel):
    command: str = Field(description="One shell command to run next (ignored if done)")
    done: bool = Field(description="True when the task is fully complete")


class MplAgent(BaseAgent):
    def __init__(
        self,
        model_name: str,
        chart: str | None = None,
        max_ticks: int = 60,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._llm = LiteLLM(model_name=model_name)
        self._chart = chart or str(Path(__file__).parent / "terminal.mpl")
        self._max_ticks = int(max_ticks)

    @staticmethod
    def name() -> str:
        return "mpl-terminal"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        counters = {"in": 0, "out": 0, "parse_failed": False}

        agent_mod = mpl.HostModule("agent")

        @agent_mod.export
        def observe() -> str:
            return session.capture_pane()

        @agent_mod.export
        def decide(obs: str) -> str:
            prompt = (
                "You are operating a Linux terminal to complete a task. Work one "
                "shell command at a time.\n\n"
                f"TASK:\n{instruction}\n\n"
                f"CURRENT SCREEN:\n{obs}\n\n"
                'Reply as JSON: {"command": "<the single next shell command, or empty '
                'if nothing left to do>", "done": <true if the task is fully complete>}.'
            )
            raw = self._llm.call(prompt, response_format=Decision)
            counters["in"] += self._llm.count_tokens(
                [{"role": "user", "content": prompt}]
            )
            counters["out"] += self._llm.count_tokens(
                [{"role": "assistant", "content": raw}]
            )
            try:
                d = Decision.model_validate_json(raw)
            except Exception:
                counters["parse_failed"] = True
                return DONE_SENTINEL
            return DONE_SENTINEL if d.done else d.command

        @agent_mod.export
        def act(command: str) -> str:
            session.send_keys([command, "Enter"], block=True)
            return session.capture_pane()

        model = mpl.load(self._chart)
        sim = mpl.Simulation(model, seed=0)
        sim.register_host(agent_mod)
        sim.validate_hosts()

        for _ in range(self._max_ticks):
            if not getattr(sim, "running", True):
                break
            try:
                sim.tick(0.1)
            except mpl.SimulationStopped:
                break
            try:
                if sim["Agent/finished"]:
                    break
            except Exception:
                pass

        return AgentResult(
            total_input_tokens=counters["in"],
            total_output_tokens=counters["out"],
            failure_mode=(
                FailureMode.FATAL_LLM_PARSE_ERROR
                if counters["parse_failed"]
                else FailureMode.NONE
            ),
        )
