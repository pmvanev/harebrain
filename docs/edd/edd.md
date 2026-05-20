![EDD glyph: chartreuse EXPECT block, "prove" arrow, evidence checkmark box](images/glyph.svg)

# Expectation-Driven Development

*A validation framework for the age of AI agents — the editor's tools, not the author's.*

By Andrea Laforgia / [a4al6a.substack.com](https://a4al6a.substack.com)

---

## The problem nobody wants to talk about

Here's an uncomfortable truth about working with AI coding agents: **we can't review their output.**

Not "we choose not to." We *can't*. Not meaningfully.

An AI agent can produce hundreds of lines of working code in seconds. A human reviewing that code line-by-line needs minutes, sometimes hours. The economics don't work. And it's getting worse — agents are getting faster, and the code they produce is getting more complex.

So what do teams actually do? They glance at the diff, run the existing tests, maybe squint at the architecture, and merge. We've replaced "trust but verify" with "trust and hope the CI is green."

This isn't sustainable. But I don't think the answer is "just write more tests" either.

## Where TDD and BDD leave a gap

Let me be clear: I'm not here to bury Test-Driven Development. TDD is one of the most important ideas in software engineering, and it works well with AI agents as well.

But TDD has a scope problem. It excels at specifying precise, deterministic behaviors — this input produces that output. It's less natural for expressing the kind of requirements that live in the gaps: the relationship between multiple behaviors, the qualitative expectations ("the error message should be helpful, not cryptic"), the systemic properties ("this must hold even under high load"). These requirements are real. They matter to users. And they tend to live in the developer's head, unwritten, because there's no natural place to put them in a test file.

There's also a phase problem. Before you can write a test, you need to know *what* to test. The design-time exploration — "what should this feature actually do, in all its edge cases?" — happens before TDD begins. It usually happens informally: in Slack, in a meeting, in someone's head. It's rarely captured.

BDD (Behavior-Driven Development) gets closer. Its Given/When/Then syntax forces you to think about behavior from the outside in, and its natural-language layer bridges the gap between business intent and executable code. But BDD's formalism — specific frameworks (Cucumber, SpecFlow, Behave), step definitions, glue code — is also its strength: it's what makes BDD scenarios executable and rerunnable. That rigor has a cost, though. It constrains how you express requirements. Some expectations are hard to fit into a three-line template.

What if we could keep the *intent* of BDD — specify behavior, then verify it — while trading some of its formalism for the flexibility to capture the full picture?

## Enter *Expectation-Driven Development*

The idea is simple, maybe deceptively so:

**Step one — Formulate expectations in plain text.**

Not in a formal Given/When/Then template, though you can use that structure if it helps. Not in a programming language. In the same natural language you'd use to explain the feature to a colleague.

For example:

> **Expectation — Cart total calculation**
>
> When a user adds multiple items to their cart, the total should reflect the sum of all item prices multiplied by their quantities. If a discount code is applied, the discount should be calculated on the pre-tax subtotal, not on individual items. Tax is applied after the discount. If the cart is empty, the total should be zero, not an error.

Notice what this captures that a unit test wouldn't: the *relationship* between discount and tax ordering, the empty cart edge case framed as an expectation about behavior (zero, not error), and the implicit requirement that this should work with "multiple items" — not just the two items in your test fixture.

You can go further:

> **Expectation — Race condition in concurrent booking**
>
> If two users attempt to book the last available slot at the same time, exactly one should succeed and receive a confirmation. The other should receive a clear rejection — not a timeout, not a double booking, not a corrupted state. This must hold even under high load.

Try writing that as a unit test. You'll end up with a page of setup code that obscures the actual expectation. To be fair, nobody writes concurrency verification as a unit test — this would be an integration or stress test. But that's the point. EDD's job here isn't to replace the concurrency test. It's to make sure someone writes one, and that it tests the right thing. The expectation captures the requirement precisely; the test implements the verification.

**Step two — Hand the expectations to the AI agent.**

The agent implements the feature. It has the full context of your codebase, your expectations, and its own understanding of best practices.

**Step three — Ask the agent to prove it.**

This is the key step. Don't just ask "did you implement it?" Ask: **"Prove to me that each expectation is fulfilled. Show me specific scenarios with concrete inputs and the outputs the system produces."**

The agent should respond with evidence like:

> **Evidence — Cart total calculation**
>
> *Scenario 1:* Added "Widget" ($10.00, qty 2) and "Gadget" ($25.00, qty 1). Subtotal: $45.00. Applied discount code "SAVE10" (10% off). Discount: −$4.50. After discount: $40.50. Tax (8%): $3.24. **Total: $43.74.**
>
> *Scenario 2:* Empty cart. `GET /api/cart/total` returns `{ "total": 0.00, "items": [] }` with HTTP 200. **No error thrown.**
>
> *Scenario 3:* Added "Widget" ($10.00, qty 1). No discount. Tax (8%): $0.80. **Total: $10.80.** Tax applied to full subtotal, not discounted amount (no discount to apply).

**Step four — Evaluate, challenge, iterate.**

Read the evidence critically. Does it actually cover the expectation? Did the agent dodge the hard part? Are the numbers right? Push back:

> You showed the discount applied to the subtotal, but you didn't show what happens if someone tries to apply two discount codes. What happens then?

The agent revises. New evidence is produced. You iterate until convergence.

**Step five — The evidence becomes the documentation.**

When you're done, you have something valuable: a set of expectations paired with concrete proof that the system meets them. This isn't a test suite that requires a framework to run. It's not a wiki page that was outdated the day it was written. It's a living record of what the system does and why, backed by specific examples.

## The workflow, visualized

```
Human: Formulates expectations (plain text)
  │
  ▼
AI Agent: Implements the feature
  │
  ▼
Human: "Prove it meets the expectations"
  │
  ▼
AI Agent: Produces evidence (concrete scenarios, inputs, outputs)
  │
  ▼
Human: Reviews evidence ──── Satisfied? ──── YES ──→ Document & ship
  │
  NO
  │
  ▼
Human: Challenges, adds expectations
  │
  └──────── Loop back to AI Agent ────────────┘
```

## This isn't a new idea (and that's a good thing)

If you've been in software long enough, you're probably thinking: "This sounds like Specification by Example." You're right. It does.

EDD stands on the shoulders of a long lineage of ideas that share the same core insight — that concrete examples in human-readable form are the best way to specify and verify software behavior:

- **Specification by Example** (Gojko Adzic, 2011) — uses concrete examples collaboratively authored by the team as both specifications and tests. The bible for this way of thinking.
- **FIT / FitNesse** (Ward Cunningham, ~2002) — executable acceptance tables written in near-plain-English, verified automatically against the system.
- **Concordion** — specifications written in natural language that become executable through instrumentation.
- **Design by Contract** (Bertrand Meyer, Eiffel) — preconditions, postconditions, and invariants as formal specifications embedded in code.
- **Property-based testing** (QuickCheck and descendants) — addresses the "not just the two items in your test fixture" problem by generating many inputs from declared properties.

So what's actually new here? Not the idea of specifying behavior in natural language. Not the idea of verifying with concrete examples. What's new is the *execution context*.

In Specification by Example, a human team collaborates to write examples, then a developer writes glue code (step definitions) to make them executable. The bottleneck is the glue code — it's tedious, it breaks when the code changes, and it requires a framework.

In EDD, the LLM *is* the glue code. It interprets natural-language expectations directly, without step definitions, without a framework, without the ceremony. And the verification loop is conversational — you challenge, the agent responds, you push back — rather than pass/fail binary.

That's a meaningful difference. But I want to be honest that it's an evolutionary one, not a revolutionary one. If you've read Adzic's work, you'll feel at home here. If you haven't, go read it — it will make you better at EDD.

There's one more thing EDD inherits from Specification by Example: the question of *who writes the expectations*. In the Specification by Example tradition, examples are collaboratively authored in "specification workshops" — conversations between developers, testers, and business stakeholders. EDD as I've described it is a solo workflow: one human, one agent. But most software is built by teams. If different team members write expectations for the same feature, they may express different — or contradictory — assumptions. If only one person writes them, you've concentrated a single point of failure in that person's understanding. I don't have a neat answer for this yet. My instinct is that expectations should be written collaboratively, then the conversation with the agent happens individually. But this is an open question.

## Why this might actually work

**It plays to human strengths.** Humans are better at judging than producing. We're excellent critics and mediocre typists. EDD lets us do what we do best: specify intent, evaluate outcomes, spot what's missing.

**It plays to AI strengths.** AI agents are fast, tireless implementers that can generate both code and evidence at scale. The bottleneck was never "can the AI write the code?" It was "can we trust the code the AI wrote?" EDD creates a structured trust-building process.

**Natural language captures what formal tests can't.** "The error message should be helpful, not cryptic." "The response time should feel instant for typical queries." "The fallback behavior should be graceful, not surprising." These are real requirements that matter to users. They're nearly impossible to express in `assert` statements, but an LLM can interpret them. A caveat: for subjective qualities like "helpful" or "graceful," the LLM will tend to judge its own output favorably — it's the fox-guarding-the-henhouse problem again. For these expectations, the human's judgment in Step 4 becomes especially critical. Don't outsource taste.

**It forces you to think before coding — the best part of TDD, without the ceremony.** The discipline of TDD was never really about the tests. It was about the act of specifying behavior before implementation. EDD preserves that discipline. You still think first. You just express your thinking in a more natural medium.

**The evidence trail creates accountability.** Every expectation has a proof artifact. Six months from now, when someone asks "does the system handle concurrent bookings correctly?", you don't grep through test files. You read the expectation and its evidence.

## Why this might *not* work (the honest part)

I believe in this idea, but I'd be dishonest if I didn't confront its weaknesses head-on. There are real problems here.

### The fox guarding the henhouse (and the deeper problem beneath it)

This is the big one, and it has two layers.

**Layer 1: Bias.** You're asking the same AI that wrote the code to produce evidence that the code works. That's like asking a student to both take the exam and grade it. The AI has every structural incentive to produce evidence that confirms its implementation. If it made a subtle error in the discount calculation, it might generate scenarios that avoid the precise inputs that would reveal the bug. Not maliciously. Just because the same reasoning flaw that caused the bug will also cause it to overlook the bug in its evidence.

**Layer 2: Execution vs. narration.** This is the deeper problem, and it's one we need to confront directly. When the agent produces "evidence," what actually happened? There are two very different possibilities:

- **Executed evidence:** The agent actually ran the code — made an API call, executed a function, queried the database — and is showing you real output from a real system.
- **Generative evidence:** The agent *described* what it believes would happen, based on its understanding of the code it wrote. It narrated a plausible verification without executing anything.

These are not the same thing. Executed evidence is evidence. Generative evidence is a second assertion by the same entity that made the first assertion. It's the difference between "I tested it and here are the results" and "I'm pretty sure it would work like this."

**EDD requires executed evidence.** If the agent can't run the code and show you real outputs, you don't have verification — you have a shared hallucination dressed up in scenario format. This means EDD depends on AI agents with tool use: the ability to execute code, call APIs, run scripts, and capture actual output. Fortunately, this is where agents are headed — modern coding agents already have shell access, can run test suites, and can interact with running systems. But you must insist on it. When reviewing evidence, ask: "Did you actually run this, or are you telling me what you think would happen?" If the agent can't answer that clearly, the evidence is worthless.

**But let's be honest: not all code is executable in an agent loop.** In practice, evidence falls into three categories:

- **Directly executable:** Functions, APIs, scripts, database queries. The agent can run these and show real output. This is the gold standard.
- **Partially verifiable:** Infrastructure code (Terraform plan output), build configurations (dry runs), schema migrations (against a test database). The agent can't deploy to production, but it can show you what *would* happen. This is weaker but still useful — a Terraform plan is better than a guess.
- **Not executable in the loop:** UI rendering, production-only behavior, third-party API integrations with rate limits or authentication, code that requires manual user interaction. Here, you're back to generative evidence whether you like it or not.

For that third category, the mitigations below become critical, and you should be clear-eyed that your confidence is lower. If most of your expectations fall into category three, EDD's value proposition degrades — and you should invest more in the "Stabilize" step (converting expectations to automated tests that *can* run in CI).

**Mitigations for both layers:**

- **Be an adversarial reviewer.** Your job isn't to passively receive evidence. It's to actively challenge it. Run adversarial scenarios. Ask "what about...?" questions. Spot-check the numbers manually.
- **Demand execution receipts.** Ask the agent to show the actual command it ran and the raw output. Not a summary. The output.
- **Use a different agent to audit.** Have a second AI agent (or a different model) independently verify the evidence against the code. The fox can guard the henhouse if there's a different fox checking the first fox's work.
- **Spot-check yourself.** For critical expectations, pick one scenario and run it manually. If the agent's evidence matches reality for the one you checked, you have higher confidence in the rest.

### The reproducibility question

Here's a hard question: are the expectations rerunnable?

If I come back next week, after the code has changed, can I re-verify the expectations? If yes — how? If you're asking an AI to re-run the evidence each time, you're relying on LLM interpretation, which is non-deterministic. The same expectation might produce different evidence on different runs. The same model might interpret an ambiguous expectation differently after an update.

If the expectations *aren't* rerunnable, then what you have is a snapshot, not a safety net. Documentation, not regression protection.

**Mitigation:** EDD should complement automated tests, not replace them. The expectations drive the initial implementation and verification. But the critical paths should *also* be captured in traditional automated tests for regression. Think of expectations as the *design-time* validation tool, and automated tests as the *runtime* safety net. The expectations are the "why." The tests are the "what, forever."

There's a related versioning problem worth flagging. If you ship feature v1 with its evidence, then modify the feature in v2, the v1 evidence is now potentially misleading. Do you re-run evidence for every change? If so, you're paying the EDD cost on every iteration. If not, the documentation rots like any other documentation. Automated tests don't have this problem — they fail loudly when the code changes in ways they don't expect. EDD evidence is silent when it becomes stale. This is another reason the "Stabilize" step matters: the automated tests are your regression alarm. The expectations are your design-time conversation.

### Natural language ambiguity

I praised the freedom of natural language earlier. But freedom has a cost. Consider:

> The system should handle large uploads efficiently.

What's large? 10MB? 10GB? What's efficiently? Under 5 seconds? Without running out of memory? Without blocking other requests?

In BDD, the formalism forces you to be specific: `Given a file of 500MB / When the user uploads it / Then the upload completes within 30 seconds`. The rigidity is a feature. It prevents hand-waving.

**Mitigation:** Write expectations as specifically as you can. The freedom of natural language doesn't mean you should be vague — it means you can be specific in ways that formal syntax doesn't allow. Instead of "handle large uploads efficiently," write "a 500MB upload should complete without timeout and without consuming more than 2x the file size in memory. A 5GB upload should use streaming and never hold the full file in memory." Still natural language. But precise.

### The evidence scalability problem

If you have 5 expectations, you can carefully review 5 sets of evidence. If you have 50, you'll start skimming. If you have 200, you'll rubber-stamp.

And yet, more expectations means better coverage. There's a tension between thoroughness and human attention span.

**Mitigation:** Prioritize. Not all expectations are equal. Some protect critical business logic. Some cover edge cases that matter but don't need forensic review. Categorize expectations by risk and allocate your review attention accordingly.

## EDD vs. TDD vs. BDD — not a replacement, a complement

Let me be blunt: if you read this and think "great, I can stop writing tests," you've missed the point.

**TDD** speaks to developers, in code. It's always executable, gives you strong regression protection, and works well as a design-time thinking tool. But it captures limited nuance — an `assert` can only say so much — and it wasn't designed with AI agents in mind (though "make these tests pass" works surprisingly well).

**BDD** speaks to the whole team, in structured natural language. It's executable via step definitions, gives you strong regression protection, and captures more nuance than raw code. But it still constrains how you express requirements, and it wasn't designed for AI agents either.

**EDD** speaks to the human-AI pair, in free-form natural language. The expectations themselves aren't executable — they're text — but the protocol demands execution in Step 3. Regression protection is weak without automation (which is why the Stabilize step matters). Where EDD wins is nuance: natural language can express the qualitative, relational, and systemic requirements that formal test syntax struggles with. And it's designed from the ground up for the AI-agent workflow.

The three aren't competitors. They're layers. EDD is the *conversation layer* between human intent and AI implementation — where you say what you mean, in all its messy, nuanced, edge-case-laden glory. Then TDD or BDD takes over for the parts that need to be deterministic and repeatable.

## A practical protocol

If you want to try EDD today, here's a concrete protocol:

### 01 — Write expectations before touching code

Spend 15 minutes writing expectations for the feature. Be specific. Cover:

- The happy path
- Edge cases you've been burned by before
- Non-functional requirements (performance, error handling, security)
- Behaviors that should explicitly *not* happen

**How big should an expectation be?** Think "one behavior you'd explain in a single breath to a colleague." The cart total calculation example is about right — it covers one coherent concern (pricing math) with its key edge cases. If you find yourself writing a page-long expectation, you're probably bundling multiple concerns. Split them. If you find yourself writing a one-liner with no edge cases, you're probably being too vague. Expand it.

### 02 — Hand expectations to the AI agent with your codebase

Give the agent your expectations and let it implement. Don't hover. Let it work.

### 03 — Request executed evidence

Prompt: *"For each expectation, show me concrete evidence that the system fulfills it. Actually run the code — execute the function, call the API, run the script — and show me the real inputs and outputs. Don't describe what you think would happen; show me what actually happened. If an expectation cannot be fulfilled, explain why."*

The word "actually" is doing heavy lifting here. You want execution receipts, not narration.

### 04 — Review adversarially

For each piece of evidence:

- Do the numbers add up?
- Did the agent test the edge case or dodge it?
- What input would break this?
- Is there a scenario the expectation didn't cover that it should?

### 05 — Challenge and iterate

Add new expectations based on what you discover. Tighten vague ones. Ask "what if?" until you're satisfied.

### 06 — Stabilize

For critical paths, convert the expectations and evidence into automated tests (unit, integration, or e2e). The evidence gives you the test cases for free — you just need to make them executable and deterministic.

### 07 — Archive

The final set of expectations + evidence becomes your feature documentation. It answers "what does this do?" and "how do we know?" in one artifact.

## A disclaimer, and the deeper point

I should be upfront: I haven't battle-tested EDD on a real project. This is a proposed framework, not a field report. I'm sharing it because I think the underlying problem — how do we validate AI-generated code at the speed AI generates it? — is urgent enough that we should be thinking out loud about solutions, even imperfect ones. If you try this and it works, I want to hear about it. If you try it and it falls apart, I want to hear about that even more.

That said, I think EDD points at something deeper than a specific technique. It reflects a shift in the role of the human developer.

In the pre-AI world, we were *authors*. We wrote the code. We wrote the tests. We wrote the documentation. Our value was in production.

In the AI-agent world, we're becoming *editors*. We specify intent. We evaluate output. We challenge evidence. Our value is in judgment.

Authors need tools for writing — IDEs, compilers, debuggers. Editors need tools for *evaluating* — ways to express what they want, inspect what they got, and close the gap between the two. TDD is an author's tool. EDD is an attempt at an editor's tool.

We're early. The tooling isn't there yet. The methodology needs pressure-testing by real teams on real projects. But the direction feels right: humans specifying intent, machines producing implementations, and a structured conversation in between to build justified confidence that the two actually match.

---

The question isn't whether AI agents will write most of our code. They already do. The question is whether we'll find a way to stay confident that the code does what we intended. Expectation-Driven Development is one bet on how we get there. I'm looking for others.

---

**Sources.** Laforgia, Andrea, "Expectation-Driven Development," *a4al6a* (Substack), [a4al6a.substack.com](https://a4al6a.substack.com).
