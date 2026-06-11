![HAR glyph: a struck-through "priors" disc whose only valid arrow points into a document box labelled DOC](images/glyph.svg)

# Hallucination Augmented Recitations, *inverted*

*Cliff notes on Köksal, Aksitov & Chang, "Hallucination Augmented Recitations for Language Models" (arXiv:2311.07424) — the paper that weaponises the failure mode, and what that buys the harebrain brain.*

---

## The inversion

Every other paper in this attribution cluster treats hallucination as the disease. HAR treats it as the reagent. The move is almost perverse and entirely correct: if you want to train a model to *read the page instead of reciting its weights*, the cleanest training signal is a page whose correct answer the model's weights insist is wrong. You manufacture that page by letting the model hallucinate, then keep only the hallucinations that are (a) false-to-the-world and (b) faithful-to-the-document. What survives is a counterfactual open-book QA example: a question, a fabricated-but-internally-coherent passage, and an answer that is *only* derivable from the passage.

> **The one-line claim.** Factual open-book QA datasets reward a model for recalling what it already knows; counterfactual ones can only be answered by grounding in the supplied text — so finetuning on deliberately-hallucinated counterfactuals improves attribution by up to **+8.0 F1**, beating human-annotated factual data with 4× less data and 4× smaller models.

The paper is doing three things: naming a *multi-objective trade-off* hiding in standard open-book finetuning (recall-from-memory competes with grounding-in-context), building a pipeline that resolves it (HAR), and shipping a dataset that proves it (CF-TriviaQA, 19,327 examples). The trade-off is the insight; the pipeline is the mechanism; the numbers are the receipt.

## The trade-off everyone was finetuning past

Instruction-tuned models (T*k*-Instruct, InstructGPT) lean heavily on open-book QA in their training mix. The unexamined assumption: feed the model `(question, document, answer)` triples and it learns to attribute its answer to the document. HAR's first contribution is to point out that this is *not* what the gradient rewards. When the document merely restates a fact the model already memorised — which is the common case for a *factual* dataset built from real knowledge — the model can minimise loss by recalling the answer from its parameters and never reading the document at all. Attribution and recall are competing objectives, and factual data lets the model satisfy the easy one.

> **Why factual data is the wrong teacher.** A passage that agrees with the model's priors cannot distinguish a grounded reader from a confident reciter. The grounding signal is *masked* by the fact that recall already gives the right answer. You only learn whether the student read the book by setting an exam where the book contradicts what they thought they knew.

This is the harebrain concern stated in the language of supervised finetuning. The whole bet of `harebrain = fast LLM brain × structured game-AI cage` presumes the brain will defer to the manifest state the cage hands it. HAR is asking the prior question: *has the brain been trained to defer at all?*

## The HAR pipeline, in three filters

HAR builds on recitation-augmented generation (Sun et al., 2023) — prompting the model to first *recite* a relevant passage and then answer from it. HAR keeps the recitation and inverts the selection criterion. Three steps:

![The HAR pipeline: a TriviaQA question feeds recitation generation (PaLM 2-L, 5-shot, 24 samples at T=0.7), then a factuality filter that keeps only the counterfactual answers, then an attribution filter that keeps only answers grounded in the generated document, yielding CF-TriviaQA. A worked example shows a question about the Lace novels, a passage hallucinated to credit Judy Blume, and the observation that the only way to answer is to read the passage because recall is now wrong.](images/fig-01-pipeline.svg)
*The brain hallucinates freely; two sound-ish filters launder the output into a grounding exam. The example is the paper's own (Figure 1).*

1. **Recitation generation.** For each TriviaQA question, prompt PaLM 2-L with a 5-shot template that conditions it to emit a `(document, answer)` pair. Twenty-four samples per question at temperature 0.7 yields roughly **3 distinct answers** per question. This is the step that *invites* hallucination — high temperature, many draws, no factuality constraint.
2. **Factuality filtering.** An 8-shot PaLM 2-L prompt judges whether a generated answer matches the gold answer in meaning (not surface form — it must catch synonyms, transliterations, "Plutos" vs "Plutus"). The decision is the normalised probability of the `Yes` token. Here the polarity is inverted from every other QA system: HAR *discards* the factual answers and **keeps the false ones**. This step removes >45% of survivors.
3. **Attribution filtering.** A 5-shot prompt asks whether the document actually entails the answer; keep only pairs with `P(Yes) > 0.5`, and for each question keep the single pair with the highest attribution score. This removes a further >50%. The output is `CF-TriviaQA`: every example is counterfactual *and* grounded.

> **The two filters are a hard critic in disguise.** Step 2 enforces "false to the world"; step 3 enforces "true to the document." Neither is the LLM trusted on its own output — each is a separate judging pass, and step 3 is an NLI entailment check. This is exactly the [[llm-modulo]] move: the generator hallucinates, the critic bank decides what lands. HAR just runs the critic bank *offline, over training data,* instead of online over plans.

The worked example is the cleanest statement of the principle. Question: who wrote the *Lace* novels? Gold answer: Shirley Conran. HAR's hallucinated document attributes them to Judy Blume and answers "Judy Blume." A model finetuned on this can only be *right* by reading the (wrong-but-provided) document — its parametric memory of Shirley Conran is now a liability. That is the grounding precondition, manufactured at scale.

## The numbers

CF-TriviaQA holds 19,327 examples. Table 1 shows each filter earning its place — full pipeline scores **0.77 attribution / 0.87 counterfactuality** on NLI evaluation, versus 0.65/0.84 for attribution-filtering-only and 0.68/0.65 for factuality-filtering-only. Both filters are load-bearing; drop either and one axis collapses.

The headline experiment finetunes T5 models on TriviaQA (human factual) vs CF-TriviaQA (LLM counterfactual) and measures token-level F1 on six **out-of-domain** open-book datasets.

| Training set | TriviaQA (in-domain) | SQuAD | NQ | HotpotQA | BioASQ | AQA | AmbigQA | **OOD avg** |
|---|---|---|---|---|---|---|---|---|
| TriviaQA (human factual) | **85.2** | 79.6 | 66.5 | 69.4 | 63.4 | 42.1 | **53.2** | 62.4 |
| CF-TriviaQA (counterfactual) | 81.7 | **81.7** | **71.2** | **73.8** | **69.5** | **44.9** | 53.2 | **65.7** |

The counterfactual model wins out-of-domain by **+3.3 F1** and sweeps five of six datasets, including the multi-hop (HotpotQA), biomedical (BioASQ), and adversarial (AQA, from Bartolo et al.) sets — the cases where grounding matters most. It loses in-domain TriviaQA by 3.5, exactly as you'd expect: it has been trained *not* to trust its TriviaQA memory. Combine the two sets and you recover both (TriviaQA 85.3, OOD 65.3, Table 3) — the combined model is the practical recommendation.

![Out-of-domain token-level F1 for T5-3B finetuned on human-annotated TriviaQA (62.4), LLM-generated factual F-TriviaQA (63.6), and counterfactual CF-TriviaQA (65.7), with a +3.3 F1 bracket noting 4x less data and 4x smaller model; a right panel lists the relative improvement at each model size from 60M to 11B (4.5 to 8.0 percent) and notes that T5-3B on CF beats T5-11B on factual data.](images/fig-02-results.svg)
*Three teachers, one student size. The gain is not the LLM-generation (F-TriviaQA captures that); it is the counterfactuality on top.*

Two control experiments make the case airtight:

- **It isn't just "LLM-generated data is better."** HAR builds **F-TriviaQA** — same pipeline, but step 2 keeps the *factual* generations instead of the counterfactual ones. F-TriviaQA scores OOD 63.6 (Table 4): better than human TriviaQA's 62.4 by 1.2 (so yes, LLM generation helps a little), but well short of CF-TriviaQA's 65.7. The counterfactuality contributes **+3.3 over human, +2.1 over the LLM-factual control.** The effect is the inversion, not the generator.
- **It holds across scale.** Across T5-Small (60M) through T5-11B, the counterfactual model beats the factual one by a relative **4.5%–8.0%** (peak +8.0% at T5-Large). Most striking: T5-3B finetuned on CF-TriviaQA outperforms the **4× larger T5-11B** finetuned on TriviaQA. The cage out-scales raw parameter count.
- **Smaller brains hallucinate harder — and that's fine.** Swapping PaLM 2-L for PaLM 2-S in generation produces *31K* counterfactual examples (50% more — smaller models hallucinate more), and CF-TriviaQA<sub>PaLM 2-S</sub> scores OOD **66.0**, slightly *better* than the large-model version (Table 5). A sound-enough filter launders a noisier generator. This is the cheapest-possible-brain result, and it's the one harebrain should stare at longest.

## Where this sits in the harebrain hypothesis

The shared throughline across this four-paper cluster — [[llm-attribution-survey]], [[rag-attribution-survey]], [[hart]], and HAR — is that *attribution is the mechanism binding the fast, ungrounded brain to verifiable sources: a species of the cage's hard critic, applied to claims rather than plans.* [[llm-modulo]] supplies the architecture; the attribution papers supply the claim-level critic. HAR is the odd one out: it does not run the critic at inference, it uses the critic to **train the brain's disposition to be checkable in the first place.**

![Two-column mapping: HAR constructs on the left in oxblood, harebrain primitives on the right in blueprint, dashed arrows between matched pairs. Hallucinated recitation maps to LLM at the leaf; the provided document maps to blackboard/Manifest; counterfactual finetuning maps to deference discipline; the factuality plus attribution filters map to a hard critic on claims; the attribution NLI score maps to the seam's typed verdict; PaLM 2-S generation maps to cheap brain, strong cage.](images/fig-03-mapping.svg)
*Same shape, claims instead of plans. HAR trains the deference; harebrain runs the loop that needs it.*

| HAR | harebrain |
|---|---|
| Hallucinated recitation (PaLM 2-L samples) | LLM at the leaf — one call per state, must read context |
| The provided document (only valid source of A) | Blackboard (per-agent) / Manifest (tick-snapshot) |
| Counterfactual finetune (correct A contradicts priors) | Deference discipline — brain defers to state, not weights |
| Factuality + attribution filter (NLI grounding) | Hard critic on claims — transition guard reading the blackboard |
| Attribution score 0.77 (thresholded entailment) | The seam — host import → typed verdict |
| PaLM 2-S generation (hallucinates more, filter cleans) | Cheap brain, strong cage |

### What the paper gives harebrain

Four things, each load-bearing.

- **The grounding *precondition*, named.** harebrain's entire architecture assumes the leaf LLM will read the manifest the cage hands it rather than confabulate from its priors. HAR shows that disposition is *not free* — a model trained on factual open-book data learns to recite, not to read — and gives a concrete recipe to instil it. Before harebrain can rely on deference, the brain has to have been taught to defer. HAR is that lesson.
- **Counterfactual state as a stress test for deference.** The deepest harebrain failure mode is silent: the brain emits a plausible action that happens to match its priors, and you never learn it ignored the blackboard, because the blackboard happened to agree. HAR's counterfactual construction is the antidote as a *test harness* — feed the leaf a manifest that contradicts world knowledge and check that it follows the manifest. A harebrain conformance suite should include counterfactual manifests for exactly this reason.
- **Filters as an offline hard critic.** The factuality and attribution filters are a [[llm-modulo]] critic bank run over a corpus rather than a plan. The attribution filter in particular is an NLI entailment check — a *sound-ish* claim critic — and it is the same primitive [[hart]] and the [[rag-attribution-survey]] put at inference time. HAR's contribution is to show the critic also works as a *data refinery*: run it once, offline, and bake its judgement into the weights.
- **The cheap-brain result.** PaLM 2-S generating, large-model filtering, beats the all-large pipeline. The general principle — *a sound critic lets you downgrade the generator* — is the harebrain cost argument in miniature. If the cage is strong enough, the brain at the leaf can be small. HAR demonstrates that at training time; harebrain bets it at inference time.

### What harebrain pushes that the paper doesn't

Two extensions, both bets.

- **From training-time to inference-time deference.** HAR bakes grounding into the weights once, offline. harebrain wants the *same* check live, on every transition — the leaf reads the manifest, a guard verifies the action is entailed by the manifest, and a contradiction routes the chart rather than silently passing. HAR proves the brain *can* be made to defer; harebrain still needs the runtime guard because finetuning shifts a disposition, it does not *guarantee* it. A counterfactually-trained brain that drifts under distribution shift is still a brain that needs a cage.
- **Beyond a single document, into decaying blackboard state.** HAR's "document" is one static passage per example. harebrain's manifest is a *decaying, multi-source, system-wide* snapshot updated every tick. The counterfactual-grounding trick generalises in principle — train the leaf to answer from whatever state the cage hands it, even when that state contradicts priors — but the paper never tests grounding against state that *changes under the model's feet*. That's the harebrain regime, and it's unproven here.

> **The trap to mark.** HAR's filters are *sound-ish*, not sound. The attribution filter is an NLI model thresholded at 0.5, and CF-TriviaQA's own measured attribution is 0.77 — meaning roughly a quarter of "grounded" examples may not be. That noise is tolerable as *training* signal (gradients average it out). It is **not** tolerable as a *runtime* guard, where a single ungrounded pass is a real error. Do not promote HAR's offline NLI filter to a harebrain transition guard without re-earning soundness — the same warning [[llm-modulo]] makes about LLM-based critics, here applied to the claim-level NLI critic.

## What's worth taking away

- HAR is the cluster's *training-side* paper: where [[hart]] and the attribution surveys put the claim-critic at inference, HAR puts it in the data pipeline and trains the disposition into the brain. Both belong in the harebrain bibliography; they are complementary, not redundant.
- The inversion — *use hallucination to build counterfactuals, then keep the false-but-grounded ones* — is the reusable idea. It is a recipe for manufacturing a grounding exam at scale.
- Counterfactual state is the right stress test for harebrain's deference assumption. A conformance suite should feed the leaf manifests that contradict world knowledge and assert it follows the manifest.
- The cheap-brain result (small generator + strong filter ≥ all-large) is the cost argument harebrain leans on, demonstrated empirically at training time.
- The filters are sound-ish, not sound. They earn their keep as a data refinery; they do not transfer to a runtime guard without re-proving soundness.

---

**Sources.** Köksal, A., Aksitov, R., & Chang, C.-C. "Hallucination Augmented Recitations for Language Models." arXiv preprint, 13 Nov 2023. [arXiv:2311.07424](https://arxiv.org/abs/2311.07424) ([raw PDF in this folder](hallucination-augmented-recitations-2311.07424.pdf)). Builds on Sun et al., "Recitation-Augmented Language Models" (2023); evaluated against TriviaQA (Joshi et al., 2017), SQuAD, Natural Questions, HotpotQA, BioASQ, AmbigQA, and adversarial QA (Bartolo et al., 2020) under the MRQA setup; generation and filtering via PaLM 2 (Anil et al., 2023); NLI evaluation per Gao et al. (2023). All diagrams above are original SVGs drawn for this page.
