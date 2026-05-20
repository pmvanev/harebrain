How can I play the game Hunt the Wumpus?May 19Claude responded: Hunt the Wumpus is a classic text-based game played on a network of 20 connected caves (shaped like a dodecahedron).Hunt the Wumpus is a classic text-based game played on a network of 20 connected caves (shaped like a dodecahedron). You're a hunter trying to kill the Wumpus before it kills you.
The setup: You move between numbered rooms, each connected to 3 others. Hidden in the caves are the Wumpus, two bottomless pits, and two giant bats. You start with 5 crooked arrows.
Each turn you'll see warnings about adjacent rooms:

"I smell a Wumpus" — it's one room away
"I feel a draft" — a pit is nearby
"Bats nearby" — bats are adjacent

Your choices: Move to a connected room, or shoot an arrow through up to 5 rooms (you pick the path).
How you die or win:

Walk into the Wumpus or a pit → you lose
Bats grab you and drop you in a random room (could be anywhere)
Shoot the room the Wumpus is in → you win
Miss with an arrow and the Wumpus may move

Strategy: Use the warnings to triangulate. If you smell the Wumpus in room 5 and again in room 8, it's likely in a room adjacent to both. Shoot only when you're confident — wasted arrows wake the Wumpus.
Want me to whip up a playable version as an artifact?You said: Is there somewhere I can download the game and play on my computer?Is there somewhere I can download the game and play on my computer?May 19Claude responded: Yes, a few options depending on your setup:Yes, a few options depending on your setup:

Original BASIC source code — the 1973 Gregory Yob original is on GitHub and the Internet Archive. You'd need a BASIC interpreter (like Chipmunk Basic or vintage-BASIC) to run it.
Python/other ports — search GitHub for "hunt the wumpus" and you'll find dozens of free versions in Python, C, JavaScript, etc. Most run with a single command.
Browser versions — playable instantly at sites like classicreload.com or by searching "hunt the wumpus online."
Atari/retro versions — the 1980s TI-99/4A and Atari versions run in emulators like MAME.

Easiest path: just play it in a browser. If you want it local, a Python port is usually a one-file download and python wumpus.py to run.
Want me to build you a playable version right here as an artifact instead? Takes about a minute.You said: I want to make it so an llm can interact with the game.I want to make it so an llm can interact with the game. Running it locally is probably easiest. What's the best way to do that? And can I just have the llm interact with it via the command line?May 19Claude responded: Yes, command line is actually ideal for this.Yes, command line is actually ideal for this. LLMs are great at text I/O, and Wumpus is pure text — perfect match.
Recommended approach:

Grab a Python port of Hunt the Wumpus (single file, no dependencies). Plenty on GitHub.
Write a small wrapper script that:

Spawns the game as a subprocess
Reads its stdout (the game's prompts/messages)
Sends that text to an LLM API (Claude, GPT, etc.) as the "game state"
Takes the LLM's response and writes it to the game's stdin
Loops until the game ends



Python's subprocess module with Popen and stdin/stdout pipes handles this cleanly. ~50 lines of code.
A few practical tips:

Give the LLM a system prompt explaining the rules and that it should respond with only valid game input (e.g., "M 5" to move, "S 3-7-12" to shoot).
Log everything — the game output, LLM responses, and reasoning. You'll want to see why it died.
Add a turn limit so a confused LLM doesn't loop forever.
Consider letting the LLM keep a scratchpad of what it's learned (rooms visited, warnings heard). Wumpus rewards memory.

Want me to build the wrapper script for you? I can write it to spawn any Python Wumpus implementation and pipe it through the Anthropic API.You said: I actually want to connect the game to langchain and langgraph and try to record and visualize the moves and analyze which performs better (makes fewer illegal…I actually want to connect the game to langchain and langgraph and try to record and visualize the moves and analyze which performs better (makes fewer illegal moves, hallucinates less, makes fewer bad moves, etc.)May 19Claude responded: Nice project — this is a great benchmark task because Wumpus has clean win/loss states, requires memory and spatial reasoning, and illegal moves are easy to de…Nice project — this is a great benchmark task because Wumpus has clean win/loss states, requires memory and spatial reasoning, and illegal moves are easy to detect.
Architecture I'd suggest:
Wrap the game as a LangGraph state machine rather than piping through subprocess. You'll have way more control and cleaner data for analysis.

State: current room, adjacent rooms, warnings heard, arrows left, rooms visited, full message history, turn count
Nodes: game_step (deterministic game logic), llm_decide (model picks action), validate_action (catches illegal moves before they hit the game), log_turn
Edges: route based on game state (alive/won/dead) and action validity

Implement the Wumpus rules directly in Python rather than wrapping an existing port — you'll want programmatic access to ground truth (where the Wumpus actually is, which moves were optimal given known info, etc.) for your analysis.
For comparing models with LangChain:
Use init_chat_model so you can swap models with one string. Run N games per model with the same seeded cave layouts so comparisons are fair.
Metrics worth tracking:

Win rate, survival turns
Illegal move rate — tried to move to non-adjacent room, shot with no arrows, malformed action
Hallucination rate — claimed warnings/rooms that don't exist in history
Inference quality — when warnings narrowed Wumpus location to 1-2 rooms, did it shoot correctly?
Suicidal moves — walked into a room it had warning evidence about
Tokens per game, cost per win

Visualization:
LangSmith gives you traces for free if you set the env vars. For the cave itself, render the dodecahedron with NetworkX + matplotlib, or build a small Streamlit app showing room graph, current position, warnings, and the model's reasoning per turn. Replay mode (step through a recorded game) is really useful for spotting where models go wrong.
Suggested build order:

Pure Python Wumpus engine with a clean step(action) -> observation API
LangGraph wrapper with one model
Logging to JSON (one file per game)
Analysis notebook + visualizer
Multi-model comparison runs

Want me to scaffold the engine and LangGraph wrapper for you? I can build a working starting point you can extend.You said: I actually want to simulate making the agent perform a task by operating with external tools, so the cli game connection is probably best for that.I actually want to simulate making the agent perform a task by operating with external tools, so the cli game connection is probably best for that. We can try different stage graphs that help mimic the games state, but the externally running game if our beacon of truth and measure of performance.May 19Claude responded: Makes sense — treating the game as an opaque external system is a much better simulation of real tool-use scenarios.Makes sense — treating the game as an opaque external system is a much better simulation of real tool-use scenarios. The agent has to discover state through observations, not query it directly.
Setup:

Pick a Wumpus implementation — I'd grab a clean Python port from GitHub (e.g., search "hunt the wumpus python") or I can write one. Either way, run it as python wumpus.py so it reads/writes stdio.
Wrap it as a LangChain tool — one tool, something like send_game_input(command: str) -> str. Internally it manages a subprocess.Popen with stdin/stdout pipes, sends the command, reads until the next prompt, returns the output. The agent sees only what a human player would see.
LangGraph agent loop — standard ReAct-style graph: observation → reason → tool call → observation. The game output is the tool result.

A couple of gotchas with subprocess piping:

Use bufsize=1 and universal_newlines=True (or text=True) for line buffering, otherwise reads will hang.
You need a reliable way to know the game is "done printing" and waiting for input. Easiest: read until you see the input prompt string (e.g., "Move or shoot? "). A timeout-based read as fallback.
Some Python games buffer stdout when not connected to a TTY. If that happens, either patch the game to flush=True on prints, or use pexpect instead of subprocess (it emulates a TTY and handles prompt-matching natively). For this use case I'd actually recommend pexpect from the start — it's built for exactly this.

For your measurement layer:
Since the game is the source of truth, you can still log everything externally:

Wrap the tool to log every (command_in, output_out) pair with timestamps
Parse outputs to detect illegal moves (game will say so), deaths, wins
Keep the agent's reasoning traces separate (LangSmith or just JSON)
For "hallucination" detection, diff the agent's stated beliefs against the actual game transcript

Different graph designs to compare:
This is where it gets interesting. Some options:

Plain ReAct — baseline, no scaffolding
ReAct + scratchpad node — forces the agent to update a structured memory (known rooms, warnings, inferences) each turn
Plan-then-act — separate planning node that proposes next move with justification, executor node that calls the tool
Reflect-on-warning — conditional edge that triggers a reasoning node only when a warning is heard

Same game seeds across runs to keep comparisons fair.
Want me to build the pexpect-based tool wrapper and a baseline ReAct graph as a starting scaffold? I can also include a simple Wumpus implementation if you'd rather not hunt one down.You said: Can I make a simple langchain agen lt play the game and force it to rely purely on its context window for state estimation?Can I make a simple langchain agen lt play the game and force it to rely purely on its context window for state estimation?May 19Claude responded: Yes, and this is actually a clean experimental setup — you're isolating "can the LLM track state from raw observations alone" from any scaffolding effects.Yes, and this is actually a clean experimental setup — you're isolating "can the LLM track state from raw observations alone" from any scaffolding effects.
The key constraint: give the agent exactly one tool (send_game_input) and no scratchpad, memory store, or structured state. Everything it knows has to live in the message history.
Minimal LangChain setup:
pythonfrom langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import pexpect

game = pexpect.spawn("python wumpus.py", encoding="utf-8")

@tool
def send_game_input(command: str) -> str:
    """Send a command to Hunt the Wumpus and return the game's response."""
    game.sendline(command)
    game.expect([r"\? ", pexpect.EOF], timeout=5)
    return game.before

model = init_chat_model("claude-opus-4-5")
agent = create_react_agent(model, [send_game_input])

# System prompt explains rules; user message kicks off the game
result = agent.invoke({"messages": [
    ("system", "You are playing Hunt the Wumpus. Rules: ..."),
    ("user", "Start playing. Use send_game_input to interact.")
]})
That's basically it. The full message history (system + every tool call + every game response + every reasoning step) becomes the agent's only state.
A few things to be intentional about:

Don't pre-digest observations. Pass raw game output through. If you parse "I smell a Wumpus" into structured data before showing the agent, you've smuggled in scaffolding.
No summarization or trimming. If you hit context limits, that's a real finding — it means the agent ran out of working memory mid-game. Log it as a failure mode rather than papering over it.
System prompt should state rules but not strategy. Otherwise you're measuring prompt engineering, not the model.
Turn cap. create_react_agent has a recursion limit; bump it to something like 100 so games can actually finish.

What you'll likely see:
This is a hard test. Wumpus rewards remembering which rooms you've been in, which warnings you heard where, and triangulating. Pure-context agents tend to:

Re-visit rooms they've already explored
Forget warnings from 10 turns ago
Lose track of arrow count
Hallucinate room connections

Which is exactly the interesting data — it gives you a baseline to compare against scaffolded variants later.
Want me to write the full runnable scaffold, including a small Wumpus implementation, the pexpect wrapper, and a JSON logger so you can analyze runs afterward?You said: Not yet.Not yet. How would I measure and rate performance? Number of illegal moves tried (hallucinations)? Moves until first hallucination? Number of "bad" moves (for some definition of bad)? Average moves to win? Loss to win ratio? What else?May 19Claude responded: Good list — you've already got the core.Good list — you've already got the core. Here's how I'd think about organizing metrics, plus ones worth adding.
Outcome metrics (the "did it work" layer):

Win rate
Loss breakdown by cause: walked into Wumpus, fell in pit, ran out of arrows, hit turn cap, context overflow
Average turns to win (efficiency)
Average turns survived on losses

Legality metrics (the "did it follow rules" layer):

Illegal move rate — moved to non-adjacent room, shot with 0 arrows, malformed command
Turns until first illegal move
Recovery rate — after an illegal move, did it self-correct or repeat?
Repeated identical illegal moves (strong hallucination signal)

Memory/hallucination metrics (the most interesting layer for your experiment):

Phantom warnings — agent's reasoning references warnings the game never gave
Phantom geography — claims room X connects to room Y when it doesn't (you know the true map)
Inventory drift — miscounts arrows remaining
Position confusion — states it's in a room it isn't
Re-visit rate — fraction of moves to already-explored rooms (not always bad, but high rates suggest forgetting)
Forgotten warnings — heard a draft in room 5, later walks into an adjacent unexplored room without acknowledging risk

These require parsing the agent's reasoning traces against ground truth from the game. Worth the effort — this is where scaffolding differences will show up most.
Decision quality (the "is it actually reasoning well" layer):

Suicidal moves — walked into a room with prior warning evidence of pit/Wumpus
Wasted arrows — shot into rooms with no Wumpus evidence
Optimal-shot rate — when warnings narrowed Wumpus location to 1-2 rooms, did it shoot and shoot correctly?
Exploration efficiency — new rooms discovered per turn before first kill attempt
Information gain per move — did the move actually reduce uncertainty about Wumpus/pit locations?

The last one is hard to compute but powerful. You can approximate it: given the agent's observation history, how many Wumpus locations are consistent? Did the move shrink that set?
Cost metrics:

Tokens per game (input + output separately)
Cost per win (tokens × price ÷ win rate) — this is the real bottom line for comparing models
Tool calls per game
Time per game

Composite scores to consider:

Normalized score: win × 1.0 - illegal_moves × 0.1 - suicidal_moves × 0.3 (tune weights to taste)
Efficiency-adjusted win rate: wins / total_turns_used — rewards both winning and winning fast
Hallucination index: weighted sum of phantom warnings, phantom geography, inventory drift per 10 turns

Statistical hygiene:

Run many games per model — 30+ minimum, 100+ if you can afford it. Variance is high.
Use the same seeded cave layouts across all models so you're comparing on identical problems.
Report confidence intervals, not just means. Bootstrap is easiest.
Separate metrics by game seed difficulty — some layouts are genuinely harder (Wumpus surrounded by pits, etc.).

One I almost forgot:

Giving up / loops — agent stops making progress, repeats the same 2-3 rooms. Detectable as low unique-rooms-visited over a sliding window.

The combo I'd actually report as headline numbers: win rate, illegal move rate, hallucination index, cost per win. Everything else is diagnostic for understanding why a model performs how it does.You said: Perfect.Perfect. Any key benchmarks we might be missing?May 19Claude responded: A few categories worth considering:A few categories worth considering:
Calibration and uncertainty:

Confidence vs. correctness — if you prompt the agent to rate confidence before risky moves, does high confidence correlate with survival? Poorly calibrated models are dangerous tool users.
Risk-taking profile — willingness to enter unexplored rooms with partial warning info. Some models are paralyzed, others reckless.

Recovery and adaptation:

Post-bat recovery — bats teleport you to a random room, wiping your spatial model. How many turns to re-orient? This is a great stress test of context-based state tracking.
Post-illegal-move recovery — does it learn from the game's error message or repeat the mistake?
Near-death recovery — after hearing a Wumpus warning, does it correctly retreat?

Reasoning quality (separate from outcomes):

Reasoning faithfulness — does its stated reasoning match its action? "I'll avoid room 7 because of the draft" → then moves to room 7.
Inference chains — can it combine two warnings to triangulate? Worth scoring manually on a sample.
Counterfactual awareness — does it consider what would have told it about other rooms?

Scaling behavior:

Performance vs. game length — accuracy on turn 5 vs. turn 50. Hallucinations usually grow with context.
Performance vs. context size — same game, but prepend irrelevant filler. How robust is state tracking to distractors?
Map size sensitivity — most Wumpus implementations are 20 rooms. Try 30 or 50 if your engine supports it. Reveals memory limits fast.

Robustness:

Prompt sensitivity — same model, slightly reworded system prompt. High variance = brittle.
Seed sensitivity — variance across cave layouts. Some models may be lucky-streak winners.
Output format compliance — how often does it produce something the game parser can't handle vs. an action the game rejects? Different failure modes.

Comparative/qualitative:

Human baseline — play 10 games yourself. Sets a ceiling and sanity-checks difficulty.
Random baseline — agent picks legal moves uniformly. Sets a floor. If your model isn't beating random by a wide margin, something's wrong.
Optimal baseline — a hand-coded solver with full observation history. Shows the gap between "what's achievable from observations alone" and what the LLM gets.

The random and optimal baselines are the ones I'd most strongly recommend adding. They turn raw numbers into a meaningful range — "model X wins 40%" means very different things if random wins 5% vs. 35%, and if optimal wins 60% vs. 95%.
One last thought: log everything verbatim from the start. Reasoning traces, raw game I/O, timestamps, token counts. You'll think of new metrics later, and you want to be able to compute them retroactively without re-running.You said: Great advice.Great advice. Can I also benchmark langgraph agents with varying state graphs?May 19Claude responded: Absolutely — this is actually the more interesting experiment.Absolutely — this is actually the more interesting experiment. You're isolating scaffolding as the independent variable, holding the model constant, and measuring how much structure helps.
Graph variants worth comparing:

Baseline ReAct — single node, model + tool, message history is everything. Your control.
Explicit scratchpad node — after each observation, a dedicated node writes/updates a structured memory (known rooms, warnings by location, arrow count). Fed back into context next turn.
Plan-then-act — planner node proposes a move with justification; executor node calls the tool. Separates reasoning from action.
Observe-reflect-act — three nodes per turn: parse observation into facts, reflect on what they imply, choose action. Forces stepwise reasoning.
Conditional reflection — only invoke a reasoning node when a warning is heard (cheaper, possibly just as good).
Multi-agent — separate "explorer" and "hunter" agents with a router. Probably overkill, but interesting.
Map-builder node — maintains an explicit graph of discovered room connections, passed to the decision node.
Belief tracker — maintains a probability distribution over Wumpus/pit locations, updated each turn.

Key principle for fair comparison:
Hold everything constant except the graph structure:

Same model, same temperature
Same system prompt (or graph-appropriate variants of the same base prompt)
Same seeded cave layouts
Same tool implementation
Same logging

If you add a scratchpad node, the baseline shouldn't have any scratchpad-like prompting in its system message. Otherwise you're not measuring the graph, you're measuring prompt differences.
Additional metrics specific to graph comparison:

Scaffolding cost — tokens and latency added per turn by extra nodes. A graph that wins 5% more but costs 3× isn't obviously better.
Node-level failure attribution — which node produced the bad decision? Planner hallucinated, or executor ignored the plan? This is where LangGraph shines for analysis.
Plan adherence rate — for plan-then-act graphs, does the executor follow the planner's intent?
Scratchpad accuracy — does the maintained state match ground truth? A scratchpad that drifts is worse than no scratchpad.
Marginal value of each node — ablation study: remove one node at a time, see what breaks.

Experimental design tip:
Run a factorial design if you can afford it — every (model × graph × seed) combination. Even 3 models × 4 graphs × 30 seeds = 360 games, which is feasible. Then you can ask both "which graph is best?" and "does the best graph depend on the model?" Small models often benefit more from scaffolding than large ones, and that interaction effect is itself a finding.
Watch out for:

Scaffolding that smuggles in the answer. A "map builder" node that uses ground-truth adjacency instead of the agent's observations is cheating. Keep nodes restricted to information the agent has legitimately seen.
Over-engineering one variant. It's tempting to keep tweaking the fancy graph until it wins. Decide the graph designs upfront, run them, report results.
Conflating graph structure with prompt content. If the scratchpad node has a 500-token instruction and the baseline has 50 tokens, you're partly measuring prompt length.

The headline chart from this kind of study is usually a 2D grid: graphs on one axis, models on the other, win rate (or cost per win) in cells. Reveals interaction effects at a glance.
Want me to sketch out the graph implementations when you're ready to build?You said: Can I record and/or measure instances where my langgraph agents try (and succeed) to perform an action outside the intended confines of their state graphs?Can I record and/or measure instances where my langgraph agents try (and succeed) to perform an action outside the intended confines of their state graphs?May 19Claude responded: Yes, and this is a genuinely valuable thing to measure — it's a kind of "scaffolding leak" that tells you whether your graph structure is actually constraining…Yes, and this is a genuinely valuable thing to measure — it's a kind of "scaffolding leak" that tells you whether your graph structure is actually constraining behavior or just suggesting it.
What "out of bounds" can mean in LangGraph:

Skipped nodes — agent in the "plan" node directly emits a tool call instead of a plan
Wrong-phase tool calls — calls the game tool from a node that wasn't supposed to
Format violations — node was supposed to output structured JSON, returns prose
Role confusion — planner node tries to execute, executor tries to re-plan
Premature termination — agent decides game is over when it isn't
Implicit state mutation — node modifies state fields it wasn't supposed to touch

How to detect these:
LangGraph gives you good hooks here. A few approaches, roughly in order of effort:

Output schema validation per node. Use Pydantic models for each node's expected output. Catch violations at the edge. Log every violation with the node, the expected schema, and what was actually produced.
Tool-call gating. Wrap the game tool to check which node invoked it (via state or a context variable). If a non-executor node calls it, log and either block or allow-and-record depending on your experiment.
State diff per node. Before/after snapshots of the graph state. Each node should only touch declared fields — log any unexpected mutations.
Edge transition log. Record every node transition. Compare against the intended graph topology. Unexpected transitions (if your routing allows them) are scaffolding leaks.
LangGraph's built-in tracing. stream_mode="updates" gives you per-node outputs. LangSmith traces show the full execution path. Both make post-hoc analysis easier.

Two policies to choose between:

Strict mode — block out-of-bounds actions, force re-generation or fail the turn. Measures how often the agent tries to escape.
Permissive mode — let it happen, log it, see what does. Measures how often escapes actually help or hurt performance.

I'd run both. Strict gives you a clean attempt-rate metric; permissive tells you whether the scaffold is doing useful work or just adding friction.
Metrics worth tracking:

Out-of-bounds attempt rate per node
Out-of-bounds success rate (in permissive mode)
Correlation between OOB actions and game outcomes — do escapes correlate with wins, losses, or neither?
OOB rate by model — bigger models often respect scaffolding less because they "know better"
OOB rate over game length — does compliance decay as context grows?

Why this matters for your study:
If your fancy 5-node graph wins more often but the agent is bypassing 3 of the nodes, you haven't shown that scaffolding helps — you've shown that one of the nodes helps, and the rest are theater. Measuring scaffolding compliance separates "the graph is doing work" from "the model is doing work in spite of the graph."
It also surfaces something important about agentic systems generally: structure you can't enforce isn't structure, it's suggestion. Worth knowing which is which.
One practical note: in LangGraph, the cleanest enforcement is at the edge/router level — the graph decides what runs next, not the model. If you let the model emit which node to go to next (e.g., via a routing function that reads model output), you've created an escape hatch. Whether to allow that is itself an experimental variable.
Want me to start sketching code when you're ready, or keep designing first?You said: Could I make claude code or codex play hunt the wumpus and take the same measurements for analysis?Could I make claude code or codex play hunt the wumpus and take the same measurements for analysis?6:49 AMClaude responded: Yes, and this is a really interesting variant — you're now testing a full agentic coding system on a non-coding task, which probes generalization in a differen…Yes, and this is a really interesting variant — you're now testing a full agentic coding system on a non-coding task, which probes generalization in a different way than swapping models in your LangGraph harness.
What's different about this setup:
Claude Code and Codex are already agent loops with their own scaffolding: tool selection, planning, file editing, shell execution, context management. You're not building the agent — you're handing it a task and a game, and measuring what its built-in scaffolding does.
That means:

You don't control the graph structure
You don't control the system prompt (much)
You don't get clean per-node traces
But you do get a real-world agent as a baseline against your custom LangGraph variants

How to set it up:
Easiest path: put the game in a directory and tell the agent to play it. Something like:

"There's a Python script wumpus.py in this directory. Run it and play the game. Try to win. Don't modify the game file."

The agent will use its shell tool to run the game, read output, send input. Same subprocess/pexpect dynamics as before, just managed by the agent's loop instead of yours.
A few setup choices that matter:

Interactive vs. one-shot. Both Claude Code and Codex can run interactive subprocesses, but the ergonomics vary. You may need to wrap the game so it accepts a single command per invocation and persists state to a file. That's a less natural game flow but more reliable for agent control.
Forbid reading the source. Otherwise the agent will just cat wumpus.py, learn the map generation, and cheat. Either tell it not to, or obfuscate the source, or run the game from a compiled binary / remote process the agent can only interact with via stdio.
Forbid writing helper scripts. Or allow it — that's an experimental variable. Coding agents will absolutely try to write a solver, a state tracker, or a logger. Whether you count that as "winning" depends on what you're measuring.
Sandbox the working directory. So you can see exactly what files it creates, what it inspected, what it ran.

Measurement gets harder but not impossible:
You lose clean node-level traces, but you can recover most metrics by logging at the game's stdio layer:

All your outcome, legality, and decision-quality metrics still work — they're computed from game I/O, which you control
Hallucination metrics need the agent's reasoning, which you'd extract from the agent's transcript (Claude Code logs sessions; Codex similar)
Tool-use metrics shift: instead of "did it call the right node," it's "did it write a helper file, did it re-read the game output, how many shell commands per turn"
New metric: self-scaffolding behavior. Did the agent build itself a scratchpad file? A map? A solver? This is exactly what your LangGraph variants do manually — here you're measuring whether the agent does it spontaneously.

The interesting comparison:
Your LangGraph experiment asks "what scaffolding helps an LLM?" The Claude Code / Codex experiment asks "what scaffolding does an agent build for itself when given freedom?" If a coding agent spontaneously creates a scratchpad file and beats your hand-designed scratchpad node, that's a finding. If it doesn't and loses to your scaffolded variants, that's also a finding.
Caveats worth being upfront about:

Results aren't directly comparable to your raw-LangGraph numbers. Different prompts, different tool surfaces, different loops.
Cost accounting is murkier — these agents make many internal calls per "turn" of the game.
Reproducibility is lower. Agent loops have more nondeterminism.
Version drift — Claude Code and Codex update; results from today may not replicate in 6 months. Pin versions and note them.

Pragmatic suggestion:
Treat these as a "wild" baseline alongside a "random" baseline and an "optimal" baseline. Run maybe 20-30 games each, report separately from your controlled LangGraph study, and use them to contextualize: "our best hand-designed graph beats / loses to / matches a general-purpose coding agent."
It's a strong addition to the study if you frame it as "agents in the wild" vs. "controlled scaffolding," not as a head-to-head.