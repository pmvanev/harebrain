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

### The adapter shape (verified working)

The working agent is committed at [`agents/mpl_agent.py`](agents/mpl_agent.py), its chart at
[`agents/terminal.mpl`](agents/terminal.mpl). Both are **verified resolving `hello-world`** through
the Terminal-Bench harness with Gemini Flash (accuracy 1.0, 263/43 tokens). `perform_task`
(a) defines the host-import closures over the live `session` + an LLM built from `model_name`,
(b) loads/compiles the chart, (c) registers the closures as an `mpl.HostModule`, (d) ticks the
simulation until the chart latches `finished`, (e) returns `AgentResult`.

The real `mpl` SDK surface (from the mplv2 repo, `mpl/sdk.py` + `mpl/host.py`):

- `model = mpl.load(path)` — parse + compile a `.mpl` file to a `Model`.
- `sim = mpl.Simulation(model, seed=0)` — deterministic given the seed.
- `mod = mpl.HostModule("agent")` + `@mod.export` on **type-annotated** functions — the host imports.
  Only `bool`/`int`/`float`/`str`/`tuple→vector<N>` cross the boundary, which is why
  `observe`/`decide`/`act` all traffic in `str`.
- `sim.register_host(mod)` then `sim.validate_hosts()` — cross-checks the chart's
  `host import { … } from agent;` block against the registered signatures, fail-fast.
- `sim.tick(dt)` in a loop; read state with `sim["Agent/finished"]`.

```python
# agents/mpl_agent.py (core — see the file for prompt-building + token accounting)
import mpl
from terminal_bench.agents.base_agent import AgentResult, BaseAgent
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.lite_llm import LiteLLM


class MplAgent(BaseAgent):
    def __init__(self, model_name, chart=None, max_ticks=60, **kwargs):
        super().__init__(**kwargs)
        self._llm = LiteLLM(model_name=model_name)
        self._chart = chart or str(Path(__file__).parent / "terminal.mpl")
        self._max_ticks = int(max_ticks)

    @staticmethod
    def name():
        return "mpl-terminal"

    def perform_task(self, instruction, session, logging_dir=None):
        agent_mod = mpl.HostModule("agent")        # the join key to `... from agent;`

        @agent_mod.export
        def observe() -> str:                       # the cage's eyes
            return session.capture_pane()

        @agent_mod.export
        def decide(obs: str) -> str:                # the brain, consulted at a leaf
            raw = self._llm.call(build_prompt(instruction, obs), response_format=Decision)
            d = Decision.model_validate_json(raw)
            return "__DONE__" if d.done else d.command

        @agent_mod.export
        def act(command: str) -> str:               # the cage's hands
            session.send_keys([command, "Enter"], block=True)
            return session.capture_pane()

        sim = mpl.Simulation(mpl.load(self._chart), seed=0)
        sim.register_host(agent_mod)
        sim.validate_hosts()
        for _ in range(self._max_ticks):
            sim.tick(0.1)
            if sim["Agent/finished"]:
                break
        return AgentResult(failure_mode=FailureMode.NONE)
```

### The chart owns the loop — and one MPL constraint that shapes it

`agents/terminal.mpl` declares the contract and the control flow:

```mpl
host import {
    observe() -> string,
    decide(obs:string) -> string,
    act(command:string) -> string,
} from agent;

default machine Agent {
    vars { obs:string := ""; cmd:string := ""; steps:int := 0;
           max_steps:int := 12; finished:bool := false; }
    state Perceive; state Think; state Act; state Done;
    ENTER => Perceive;

    Perceive => Think then { obs := observe(); };          // one observe() per iteration
    Think    => Act   then { cmd := decide(obs); steps += 1; };   // one decide() per iteration
    Act when cmd == "__DONE__"                       => Done then { finished := true; };
    Act when cmd != "__DONE__" && steps >= max_steps => Done then { finished := true; };
    Act when cmd != "__DONE__" && steps < max_steps  => Perceive then { last_screen := act(cmd); };
}
```

The shaping constraint: MPL host modules want to be **"values in, values out,"** and a var written
in a `then { }` block is only readable on the *next* tick (`docs/0 - Overview.md` §6.3, §10 — no
mid-tick mutation). So each side-effecting host call (`observe`/`decide`/`act`) fires **exactly once**
on a transition, and the guards branch only on **committed** vars. That's why a loop iteration is a
three-tick `Perceive → Think → Act` pipeline rather than one fat rule — and it's the cage being
*legible*: perceive, decide, act, the step-budget guard, and termination are all visible structure,
not buried in a Python `while`. Validate chart edits fast with
[`agents/_chart_dryrun.py`](agents/_chart_dryrun.py) (stub host fns, no Docker/LLM) before a real run.

### Relation to the wumpus host-import contract

This is the same pattern the wumpus feature is built around — *"the MPL chart owns the world state
and the LLM consults at the decide-leaf via a host import"* (`docs/feature/wumpus/feature-delta.md`,
`drive-engine-from-host-import`), which was marked *blocked-on-mpl-spike* for its exact signature.
This Terminal-Bench agent is an independent, **working** instance of that contract against the real
`mpl` SDK: wumpus's host-import is snapshot→snapshot; this one is `observe`/`act`; both obey the same
rule — *the chart reaches the world only through registered host functions*.

### Environment: mpl and terminal-bench in one venv

`tb` and `mpl` install as separate uv tools (separate venvs), so the agent process can't `import mpl`
by default. Put both in one environment — simplest is to add `mpl` to `tb`'s tool venv:

```bash
uv tool install --python 3.13 --force \
  --with /path/to/mplv2 terminal-bench         # mpl is a local path package
```

Then run with `PYTHONPATH` pointing at the agent dir (so `--agent-import-path` can find it):

```bash
PYTHONPATH=/abs/.../terminal-bench/agents \
  tb run --agent-import-path mpl_agent:MplAgent \
    -m gemini/gemini-2.5-flash -t hello-world -d terminal-bench-core==0.1.1 --output-path ~/tb-runs
```

> **Never shell out to the `mpl` CLI in a non-interactive context.** Its console entry point is
> `mpl.cli.repl:main`, which **ignores its arguments** (no `--help`/`--version`) and drops straight
> into an interactive REPL that reads stdin. With no stdin/EOF it blocks forever — `mpl --help` will
> hang the shell. Embed MPL via the **Python library** (`mpl.load` / `mpl.Simulation` /
> `mpl.HostModule`), as `mpl_agent.py` does; the CLI is for humans at a terminal only.

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
That property has to live in the **cage**, not the harness: `mpl.Simulation(model, seed=0)` already
makes the chart's tie-breaks and `rand()` deterministic, so the cage's *control flow* replays
identically — the LLM `decide` leaf is then the **only** source of nondeterminism. Pin its sampling
(temperature 0 / a fixed seed where the provider supports it) and "same seed → same trace" holds.
The harness won't reward determinism, so the cage has to encode it — precisely the harebrain argument
restated from the agent side.

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

# custom mpl agent (needs mpl in tb's venv — see "Environment" above)
PYTHONPATH=/abs/.../terminal-bench/agents tb run --agent-import-path mpl_agent:MplAgent \
  -m gemini/gemini-2.5-flash -t hello-world -d terminal-bench-core==0.1.1 --output-path ~/tb-runs
```
