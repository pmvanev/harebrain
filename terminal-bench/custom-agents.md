# Running Terminal-Bench against a custom agent

How to make Terminal-Bench score **your own agent** — first a plain Python agent, then an
**MPL-chart-driven** agent (the harebrain cage). Read [`README.md`](README.md) first for setup and
the Windows/WSL2 caveat; everything below assumes a working harness (i.e. running from WSL2/Linux
on this machine).

All facts here are read off the installed package (`terminal-bench 0.2.18`):
`terminal_bench/agents/base_agent.py`, `agent_factory.py`, `naive_agent.py`,
`terminal/tmux_session.py`, `cli/tb/runs.py`.

---

## The agent contract

An agent is a subclass of `terminal_bench.agents.base_agent.BaseAgent` with exactly two required
members:

```python
class BaseAgent(ABC):
    @staticmethod
    @abstractmethod
    def name() -> str: ...

    @abstractmethod
    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult: ...
```

The mental model — and this is the part that matters for harebrain:

> **Your agent runs on the host. Its only hands inside the task are a tmux session.**
> The harness builds the Linux task container, attaches a tmux session to it, and hands you that
> `session`. You decide what to type; you type it with `session.send_keys(...)`; you read the screen
> with `session.capture_pane()`. You never get the container filesystem directly — you act *through
> the terminal*, exactly like a human at a prompt. Grading happens **after** `perform_task` returns:
> the harness runs the task's hidden tests against the container's final state.

### What you get from `TmuxSession`

Real signatures (from `terminal/tmux_session.py`):

```python
session.send_keys(keys: str | list[str], block: bool = False,
                  min_timeout_sec: float = 0.0, max_timeout_sec: float = 180.0)
session.capture_pane(capture_entire: bool = False) -> str   # current screen (or full scrollback)
session.get_incremental_output() -> str                     # new output since last read
session.get_asciinema_timestamp() -> float                  # for AgentResult.timestamped_markers
session.is_session_alive() -> bool
```

`send_keys(["ls -la", "Enter"], block=True)` runs a command and waits for the shell to return
(up to `max_timeout_sec`). Without `block`, it fires and returns immediately — use that for
interactive programs, then poll `capture_pane()`.

### What you return — `AgentResult`

```python
AgentResult(
    total_input_tokens: int = 0,
    total_output_tokens: int = 0,
    failure_mode: FailureMode = FailureMode.NONE,   # NONE on a normal finish
    timestamped_markers: list[tuple[float, str]] = [],
)
```

Token counts feed the cost/efficiency reporting; they don't affect pass/fail. Return
`FailureMode.NONE` for an ordinary completion (resolved-or-not is decided by the tests, not by you).
There are specific modes for agent-side failures (e.g. `FATAL_LLM_PARSE_ERROR`); see
`agents/failure_mode.py`.

## How the CLI wires `--model` and `--agent-kwarg` into your constructor

From `cli/tb/runs.py::_process_agent_kwargs` → `AgentFactory.get_agent(..., **kwargs)` →
`agent_class(**kwargs)`:

- `--model provider/name` arrives as the **`model_name`** kwarg (string, litellm style).
- each `--agent-kwarg k=v` arrives as kwarg `k="v"` (string; parse/convert yourself).

So declare `def __init__(self, model_name: str, **kwargs)` and you'll receive the model. Build your
own LLM client from it — the simplest is the bundled litellm wrapper:

```python
from terminal_bench.llms.lite_llm import LiteLLM
llm = LiteLLM(model_name=model_name)          # reads the matching provider API key from env
text = llm.call(prompt)                        # optional: response_format=<pydantic model>, logging_path=...
n = llm.count_tokens([{"role": "user", "content": prompt}])
```

(You are not obliged to use `LiteLLM` — a custom agent may call any client. But `--model` only means
anything if your constructor consumes `model_name`.)

## Making your agent importable

`--agent-import-path` does `importlib.import_module(module)` **inside the `tb` process**. The module
must be on that process's `sys.path`. Two clean options:

**A. Run `tb` from a project venv that has both** (recommended):

```bash
uv init tb-agents && cd tb-agents
uv add terminal-bench
# put your agent at tb-agents/myagents/command_loop.py
uv run tb run --agent-import-path myagents.command_loop:CommandLoopAgent \
  --model gemini/gemini-2.5-flash --dataset-path /abs/path/to/tasks -t hello-world
```

**B. Keep the global tool install and inject `PYTHONPATH`:**

```bash
PYTHONPATH=/abs/path/to/your/agent/dir tb run \
  --agent-import-path command_loop:CommandLoopAgent --model gemini/gemini-2.5-flash ...
```

---

## Part 1 — a custom Python agent

The minimal *useful* agent is a perceive→think→act loop: show the model the screen, ask for the next
shell command(s), run them, repeat until the model says it's done or you hit a step budget.
`NaiveAgent` (single shot) and `Terminus2` (full loop) are the reference implementations; this is a
compact loop in between.

```python
# myagents/command_loop.py
from pathlib import Path
import json
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

    def perform_task(self, instruction, session: TmuxSession,
                     logging_dir: Path | None = None) -> AgentResult:
        in_tok = out_tok = 0
        screen = session.capture_pane()

        for _ in range(self._max_steps):
            prompt = (
                "You are operating a Linux terminal to complete a task.\n"
                f"TASK:\n{instruction}\n\n"
                f"CURRENT SCREEN:\n{screen}\n\n"
                "Reply as JSON: {\"commands\": [...], \"done\": bool}."
            )
            raw = self._llm.call(prompt, response_format=Step)
            in_tok += self._llm.count_tokens([{"role": "user", "content": prompt}])
            out_tok += self._llm.count_tokens([{"role": "assistant", "content": raw}])

            try:
                step = Step.model_validate_json(raw)
            except Exception:
                return AgentResult(total_input_tokens=in_tok, total_output_tokens=out_tok,
                                   failure_mode=FailureMode.FATAL_LLM_PARSE_ERROR)

            for cmd in step.commands:
                session.send_keys([cmd, "Enter"], block=True)

            screen = session.capture_pane()
            if step.done:
                break

        return AgentResult(total_input_tokens=in_tok, total_output_tokens=out_tok,
                           failure_mode=FailureMode.NONE)
```

Run it:

```bash
tb run --agent-import-path myagents.command_loop:CommandLoopAgent \
  --model gemini/gemini-2.5-flash --agent-kwarg max_steps=20 \
  --dataset-path /abs/path/to/tasks -t hello-world --output-path runs
```

That's the entire contract. Everything sophisticated (Terminus's structured analysis/plan/commands
format, retry-on-context-overflow, per-key durations) is elaboration on this loop.

> **Aside — wrapping an existing CLI instead.** If your "agent" is a tool you install *inside* the
> container (like Claude Code or OpenHands), subclass `AbstractInstalledAgent`
> (`agents/installed_agents/`) instead of `BaseAgent`: you provide a setup script (`.sh`/`.j2`) that
> installs the tool in the container and a command template that invokes it. For a harebrain agent
> we want the **host-side `BaseAgent`** path, because the *cage runs on the host* and only its
> actions cross into the container.

---

## Part 2 — a custom MPL agent (the harebrain cage)

This is the interesting one, and it falls out of the contract almost for free, because the
Terminal-Bench agent boundary *is* the harebrain seam.

### The mapping

harebrain = **fast LLM brain × structured game-AI cage**. An MPL chart is the cage: a hierarchical
state machine whose control flow is authored and whose leaves consult an LLM. Drop that onto the
Terminal-Bench contract and every piece has a home:

| harebrain / MPL | Terminal-Bench | concretely |
|---|---|---|
| the world the cage acts on | the Docker container's terminal | — |
| **act** host-import | `session.send_keys([...], block=True)` | the chart's hands |
| **observe** host-import | `session.capture_pane()` / `get_incremental_output()` | the chart's eyes |
| **decide-leaf** (the brain) | an `llm.call(...)` from inside a chart leaf | the model, consulted |
| the chart / HSM topology | *your* `perform_task` driving the MPL runtime | the cage |
| guards / explicit terminal states | loop/guard logic in the chart | "stop when tests would pass" / step budget |
| `model_name` from `--model` | the model the decide-leaf calls | same ruler, swappable brain |

This is exactly the host-import pattern the wumpus feature is built around — *"the MPL chart owns the
world state and the LLM consults at the decide-leaf via a host import"*
(`docs/feature/wumpus/feature-delta.md`, job `drive-engine-from-host-import`). There, the host-import
takes an opaque **snapshot** and returns a new snapshot. Here the "world" is a live terminal rather
than a wumpus engine, so the two host-imports are `observe()` (snapshot of the screen) and
`act(keystrokes)` (advance the world) instead of a single snapshot→snapshot step — but it is the same
contract: **the chart never touches the world directly; it reaches it only through registered host
functions.**

### The adapter shape

A custom MPL agent is a `BaseAgent` whose `perform_task` (a) boots the MPL runtime on the chart,
(b) registers `observe`/`act` host-imports backed by the `session`, (c) wires the decide-leaf to an
LLM built from `model_name`, (d) runs the chart to a terminal state, (e) returns `AgentResult`.

```python
# myagents/mpl_agent.py
from pathlib import Path
from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.lite_llm import LiteLLM
from terminal_bench.terminal.tmux_session import TmuxSession

# from harebrain_mpl import load_chart, Runtime   # <-- the MPL runtime (API TBD; see note below)


class MplAgent(BaseAgent):
    def __init__(self, model_name: str, chart: str = "agents/terminal.mpl", **kwargs):
        super().__init__(**kwargs)
        self._llm = LiteLLM(model_name=model_name)
        self._chart_path = Path(chart)

    @staticmethod
    def name() -> str:
        return "mpl-terminal"

    def perform_task(self, instruction, session: TmuxSession,
                     logging_dir: Path | None = None) -> AgentResult:
        tokens = {"in": 0, "out": 0}

        # --- host imports: the cage's only contact with the world ---
        def observe() -> str:
            return session.capture_pane()

        def act(keystrokes: str) -> str:
            session.send_keys([keystrokes, "Enter"], block=True)
            return session.capture_pane()

        # --- decide-leaf: the brain ---
        def decide(prompt: str) -> str:
            tokens["in"] += self._llm.count_tokens([{"role": "user", "content": prompt}])
            out = self._llm.call(prompt)
            tokens["out"] += self._llm.count_tokens([{"role": "assistant", "content": out}])
            return out

        # --- run the chart: cage owns control flow, calls host imports + decide-leaf ---
        # chart = load_chart(self._chart_path)
        # runtime = Runtime(chart, host_imports={"observe": observe, "act": act, "decide": decide})
        # runtime.run(inputs={"instruction": instruction})       # runs to a terminal state
        raise NotImplementedError("wire to the harebrain MPL runtime once its host-import API is pinned")

        return AgentResult(total_input_tokens=tokens["in"],
                           total_output_tokens=tokens["out"],
                           failure_mode=FailureMode.NONE)
```

```bash
tb run --agent-import-path myagents.mpl_agent:MplAgent \
  --model gemini/gemini-2.5-flash --agent-kwarg chart=agents/terminal.mpl \
  --dataset-path /abs/path/to/tasks -t hello-world --output-path runs
```

**What's pinned vs. what's TBD.** The Terminal-Bench side is exact (the three closures above are the
entire integration surface). The MPL side — `load_chart` / `Runtime` / how host-imports are
registered — is **not yet pinned in this repo**: the wumpus feature-delta marks the host-import
signature as *blocked-on-mpl-spike* (`feature-delta.md` job `drive-engine-from-host-import`,
US-10 host-import-determinism-contract). When that spike lands, the only change here is replacing the
three commented lines with the real registration call; the closures don't move.

### Why this is the demonstration worth running

This is the harebrain hypothesis as a measurable experiment, on the ruler the whole
[research-summaries set](../docs/research-summaries/terminal-bench/terminal-bench.md) points at:

- Hold `--model` fixed and swap `--agent` between `command-loop` (a thin scaffold) and `mpl-terminal`
  (the cage). The delta is the **value of the cage at a fixed brain** — the exact "harness lever" the
  [Meta-Harness](../docs/research-summaries/meta-harness/meta-harness.md) and
  [agent-harness-anatomy](../docs/research-summaries/agent-harness-anatomy/agent-harness-anatomy.md)
  summaries argue is the dominant tunable surface at the frontier.
- Hold the chart fixed and swap `--model`. A cage worth keeping should *transfer* — the model-swap
  test from the Meta-Harness summary, run on your own chart.

### One caveat the cage must own itself: determinism

Terminal-Bench grades on the container's **final state**, not on your trajectory, and it allows
network access — so the *benchmark* is not deterministic-given-seed (see the determinism row in the
[summary's harebrain mapping](../docs/research-summaries/terminal-bench/terminal-bench.md#where-this-sits-in-the-harebrain-hypothesis)).
That property has to live in the **cage**, not the harness: if you want "same seed → same trace,"
the chart's decide-leaf must pin sampling (temperature/seed) and the chart must avoid nondeterministic
host-imports. The harness won't reward determinism, so the cage has to encode it — which is precisely
the harebrain argument restated from the agent side.

---

## Quick reference

```bash
# free harness check (no API spend)
tb run --agent oracle  -t hello-world --dataset-path $TASKS --output-path runs   # should resolve
tb run --agent nop     -t hello-world --dataset-path $TASKS --output-path runs   # should fail

# built-in loop agent
tb run --agent terminus-2 -m gemini/gemini-2.5-flash -t hello-world --dataset-path $TASKS

# custom python agent
tb run --agent-import-path myagents.command_loop:CommandLoopAgent -m gemini/gemini-2.5-flash \
  -k max_steps=20 -t hello-world --dataset-path $TASKS

# custom mpl agent
tb run --agent-import-path myagents.mpl_agent:MplAgent -m gemini/gemini-2.5-flash \
  -k chart=agents/terminal.mpl -t hello-world --dataset-path $TASKS
```
