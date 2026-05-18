![Statechart glyph: XOR-decomposition box, transition arrow, AND-decomposition box](images/glyph.svg)

# MPLv2, read against Harel's *Statecharts*

*A summary of `github.com/lostinplace/mplv2` framed by the 1987 paper "Statecharts: A Visual Formalism for Complex Systems" (Harel, Sci. of Computer Programming 8).*

---

## What the paper proposed

Harel's thesis is that the conventional flat state-transition diagram cannot describe a non-trivial reactive system without exploding combinatorially. His fix — *statecharts* — is a compact extension of state diagrams along three axes:

> statecharts = state-diagrams + depth + orthogonality + broadcast-communication

- **Depth** — states *cluster* into super-states (XOR-decomposition); a single arrow leaving a super-state stands in for an arrow leaving every substate, and arrows may originate or terminate at *any* level (inter-level transitions).
- **Orthogonality** — states *split* via dashed lines into AND-components that are simultaneously active. The combined state of two orthogonal regions with *n* and *m* substates is conceptually *n×m* without ever drawing *n·m* boxes. Components may synchronize on shared events or depend on each other via `in(state)` conditions.
- **Broadcast communication** — an event raised by one component is visible to *every* region that cares to react. There is no addressing.

The paper also catalogs a handful of supporting devices: *default* arrows (initial state), *history* entrances (`H` and deep `H*`), conditional and selection connectives, transitions guarded by conditions, and Mealy-style outputs/actions on arrows. Harel works the entire formalism out on a single running example — the Citizen Quartz Multi-Alarm III wristwatch — arriving at the foldout statechart of Fig. 31.

## What MPLv2 is

MPLv2 is a textual DSL plus a Python simulation engine for the same class of systems Harel had in mind: reactive, event-driven, hierarchical, concurrent. It compiles `.mpl` source via `lark` into a rule set executed tick-by-tick over an immutable *Manifest*.

Its surface vocabulary maps onto Harel's almost line-for-line, with a few deliberate deviations — an explicit synchronous tick model, declared signal interfaces, deterministic conflict resolution, and first-class spatial data.

## The mapping

| Harel (1987) | MPLv2 construct | Notes |
|---|---|---|
| XOR-decomposition (clustering / refinement) | `state X { state A; state B; default state A; }` | Exactly one child active. Direct correspondence to Harel's rounded-box nesting. |
| AND-decomposition (orthogonality, dashed-line split) | `machine X { state A; state B; ... }` | Machines are the AND-container; multiple child regions are simultaneously active. MPLv2 distinguishes the two kinds of container *lexically* rather than typographically. |
| Default arrow (initial substate) | `default state Idle;` and the `ENTER => ...` rule | Same semantics as Harel's small-dot arrow. |
| Transition with event / condition / action (`e[C]/a`) | `Src when cond => Dst then { action; }` | `=>` is Harel's transition arrow. `when` is the bracketed condition. `then { }` is the Mealy action (§5 of the paper). |
| Activities / continuous actions in a state (§5) | `Running -> { fuel -= 1; };` | The *observation* operator `->` — doesn't exit the source — corresponds to Harel's "activity" attached to a state. |
| Broadcast event (§3, §5) | Signals on the canonical bus `SIGNALS/X` + `receives { X } from { * }` | MPLv2 keeps Harel's broadcast model but *declares the interface*: a machine only hears what it explicitly subscribes to. Undeclared signals are inert. |
| "in (state)" condition (§3) | Same notion; cross-machine path references in `when` clauses | One orthogonal component can guard on another's active substate. |
| Conditional connective (C-entrance, Fig. 33) | `choose(N) { @priority(...) ...; @weight(...) ...; }` | `choose` generalizes Harel's C-connector: instead of one of N branches selected by a condition, MPLv2 selects up to N from a competing pool, using priority then weight then seeded RNG. |
| Inter-level transitions and "exit independently" | Path-qualified targets: `=> Machine/Sub/Leaf`, `=> EXIT` | Arrows in MPLv2 are fully qualified paths rather than diagram positions, so they cross hierarchy levels naturally. |
| Delays and timeouts (§4.2, e.g. "2 min in date") | Tick-counter idioms over `vars` driven by `TICK/elapsed` | Not a dedicated construct; the synchronous tick model makes timeouts a trivial guard expression. |
| △ History entrance `H` / deep `H*` (§2) | — not a first-class construct — | Harel's "enter the most recently visited substate" connector has no direct equivalent in MPLv2 today. It would have to be emulated with a `vars` slot holding the last-active child and a guarded re-entry rule. |
| △ Selection connective `S` (Fig. 34) | — emulated with labelled signal payloads — | MPLv2's `signal as label` with per-payload iteration covers the "event value selects target" case at the rule level rather than the diagram level. |

## What MPLv2 adds beyond the paper

These features extend rather than mirror Harel; they're choices the engine makes precisely because it has to *run*, not just be drawn.

### A synchronous tick with explicit next-tick causality

Statecharts (in the 1987 paper) leave step semantics informal — STATEMATE later filled in synchronous and super-step models. MPLv2 commits to one discrete tick: rules evaluate against Manifest_t, propose changes, and the changes land atomically in Manifest_t+1. Signals emitted at *t* are visible at *t+1*. This sidesteps Harel's "instantaneous chain reaction" ambiguity.

### Deterministic conflict resolution

The paper acknowledges that competing transitions can deadlock or nondeterminize a step and warns the modeler to "carefully avoid" contradictions (Fig. 18). MPLv2 takes the opposite stance: contradictions are *expected*, and a three-stage pipeline picks a winner every time:

```
@priority(N)   — deterministic rank; highest priority group wins
@weight(W)     — weighted random among tied priorities
seeded RNG     — uniform tie-break, reproducible per simulation seed
```

This turns "a robot wants to chase AND retreat" from a modelling bug into a modelling primitive.

### Probabilistic transitions

Section 6.3 of the paper speculates about adding probabilities; MPLv2 ships them as `@weight`. The `weighted_behavior` example exercises this.

### Typed data and vector arithmetic

Harel's statecharts are pure control; data lives in an unmentioned "activity" layer. MPLv2 makes `vars` first-class with `bool`, `int`, `float`, `string`, `vector<N>`, a coercion ladder, and conflict-resistant operators (`+=`, `*=`, `/=` merge across rules without conflict).

### Spatial regionmaps

`regionmap GalaxyMap : vector<3> { ... }` binds regions to coordinate vectors, enabling `near`, `nearest`, and `choose(N) from <map>` queries. This is a clean extension orthogonal to the Harel formalism — the watch example never needed it, but a swarm or town simulation does.

### Runtime instantiation

`new CannonProjectile into Volleys at [...] with { vars { ... } };` spawns new region trees during simulation. Statecharts in 1987 were static structural descriptions; MPLv2 treats the structure itself as dynamic.

### Strongly declared signal interfaces

Harel's broadcast is universal. MPLv2's broadcast is universal *over a declared interface*: a machine that doesn't `emit` a signal can't send it, and one that doesn't `receive` it can't hear it. This is a deliberate tradeoff — less expressive, more analyzable — matching a textual language's need for static checking that a picture doesn't have.

## How the Harel wristwatch would look in MPLv2

The watch's top-level `alive` state in Harel Fig. 27 decomposes orthogonally into `main`, four status components, `light`, and `power`. In MPLv2 that's:

```
machine Alive {
    state Main {
        state Displays { ... }
        state AlarmsBeep { ... }
    }
    state Alarm1Status { default state Disabled; state Enabled; }
    state Alarm2Status { default state Disabled; state Enabled; }
    state ChimeStatus  { ... }
    state Light        { default state Off; state On; }
    state Power        { default state OK;  state Blink; }

    ENTER spread {
        => Main/Displays/Time;
        => Light/Off;
        => Power/OK;
    }
}
```

Press-button events `a`/`b`/`c`/`d` arrive on `SIGNALS/A`…`SIGNALS/D` and reach every component that declares `receives { A,B,C,D } from { * } as btn;`. Harel's *"depressing b in update simultaneously turns on the light"* is two independent rules in two orthogonal regions reacting to the same broadcast signal — precisely the behaviour the paper highlights as the payoff of orthogonality.

## What's worth taking away

- MPLv2 is best read as a **textual, executable statechart**, with Harel's depth/orthogonality/broadcast intact and his Fig. 18-style ambiguities resolved by an explicit conflict-resolution pipeline.
- The big additions — ticks, typed data, weights, regionmaps, runtime instantiation — are the kind of pragmatic extensions any reactive *simulator* (as opposed to specification) eventually needs.
- The main expressive gap relative to the 1987 paper is **history entrances** (`H` / `H*`). They aren't built in and have to be simulated with auxiliary `vars`.
- The deliberate retreat from universal broadcast to **declared `emits` / `receives` interfaces** is the most interesting trade: it loses some of the "just react to anything anyone shouts" elegance of the diagrammatic original in exchange for static checkability of a textual program.

---

**Sources.** `mplv2/README.md`; `mplv2/docs/0 - Overview.md`; Harel, D., "Statecharts: A Visual Formalism for Complex Systems," *Science of Computer Programming* 8 (1987), pp. 231–274.
