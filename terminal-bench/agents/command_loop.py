"""A minimal custom Terminal-Bench agent: a perceive->think->act loop.

This is the worked example from ../custom-agents.md. It subclasses BaseAgent,
receives `model_name` from `--model`, drives the task by sending shell commands
into the container's tmux session, and stops when the model says it's done or a
step budget is hit.

Run (from WSL, with the model's API key exported):

    PYTHONPATH=/mnt/c/Users/PhilVanEvery/Git/github/pmvanev/harebrain/terminal-bench/agents \
      tb run --agent-import-path command_loop:CommandLoopAgent \
        -m gemini/gemini-2.5-flash -k max_steps=20 \
        -t hello-world -d terminal-bench-core==0.1.1 --output-path ~/tb-runs
"""

from pathlib import Path

from pydantic import BaseModel, Field

from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.lite_llm import LiteLLM
from terminal_bench.terminal.tmux_session import TmuxSession


class Step(BaseModel):
    commands: list[str] = Field(description="Shell commands to run this step")
    done: bool = Field(description="True when the task is complete")


class CommandLoopAgent(BaseAgent):
    def __init__(self, model_name: str, max_steps: int = 15, **kwargs):
        super().__init__(**kwargs)
        self._llm = LiteLLM(model_name=model_name)
        self._max_steps = int(max_steps)

    @staticmethod
    def name() -> str:
        return "command-loop"

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        in_tok = out_tok = 0
        screen = session.capture_pane()

        for _ in range(self._max_steps):
            prompt = (
                "You are operating a Linux terminal to complete a task.\n"
                f"TASK:\n{instruction}\n\n"
                f"CURRENT SCREEN:\n{screen}\n\n"
                'Reply as JSON: {"commands": [...], "done": bool}.'
            )
            raw = self._llm.call(prompt, response_format=Step)
            in_tok += self._llm.count_tokens([{"role": "user", "content": prompt}])
            out_tok += self._llm.count_tokens([{"role": "assistant", "content": raw}])

            try:
                step = Step.model_validate_json(raw)
            except Exception:
                return AgentResult(
                    total_input_tokens=in_tok,
                    total_output_tokens=out_tok,
                    failure_mode=FailureMode.FATAL_LLM_PARSE_ERROR,
                )

            for cmd in step.commands:
                session.send_keys([cmd, "Enter"], block=True)

            screen = session.capture_pane()
            if step.done:
                break

        return AgentResult(
            total_input_tokens=in_tok,
            total_output_tokens=out_tok,
            failure_mode=FailureMode.NONE,
        )
