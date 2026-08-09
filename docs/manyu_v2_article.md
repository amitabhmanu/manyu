# From an Affect Core to a Situated Worldview: Manyu v2

Current agents can be remarkably capable without having a point of view that is genuinely their own. They can summarize arguments, imitate positions, and retrieve patterns learned during training, but they do not normally carry an experience-derived account of what they have encountered, what evidence changed their mind, or what stance they now hold because of it. Without that continuity, an apparent “opinion” is usually a fresh synthesis of pretrained knowledge and the current prompt—not a worldview formed over time.

Yet agents do have encounters. They interact with people, receive correction, attempt work in external environments, observe tool outcomes, encounter obstruction, make repairs, and see whether an expectation holds. These are not human lived experiences, and they should not be described as such. But they are agent experiences: events with provenance, outcomes, context, and consequences for the system’s future behaviour.

The design opportunity is to let an agent learn from those experiences without hiding the learning in prompts or turning it into covert personalization. A belief core can capture evidence from governed interaction traces, update explicit and revisable beliefs, and synthesize them into a bounded worldview. With that in place, an agent does more than regurgitate what it learned during training: it can offer a qualified point of view grounded in its own recorded experience, explain the evidence behind it, and say when the evidence is not yet enough.

Manyu v2 explores this opportunity. It builds on the original Manyu question—what would it take for an agent to use affect-like regulation without turning emotion into theatre?—and asks the next one: can a bounded, inspectable worldview influence the next turn without becoming an unaccountable inner authority?

This is not a claim that Manyu is conscious, suffers, has rights, or experiences emotion as a person does. It is an engineering proposal. Manyu v2 adds persistent beliefs, synthesized worldview stances, and a constrained inner-voice/mood loop to the original affective control system. The system can now carry forward both how events regulated it and what it has provisionally learned from them.

## v1: affect as an external control loop

Original Manyu made affect operational and governable. The acting model did not own the authoritative affective state. Instead, it submitted a normalized event to a separate local service, which appraised the event, transitioned state, exposed a partial interoceptive view, and arbitrated any affect-mediated influence on action.

```text
normalized event → appraisal → affect transition → partial interoception
                 → arbitration → bounded action influence → trace
```

The separation was the point. A model can generate language that sounds anxious, warm, or disappointed within an ordinary response stream. That does not make the signal reliable, inspectable, or safe. In Manyu v1, affect was a structured control signal with provenance, decay, reason codes, and an audit trail. It could shape attention, pacing, repair orientation, and planning, but it could not create permissions or overrule safety policy.

Several v1 constraints remain non-negotiable:

- Events are normalized and assigned a trust class before appraisal.
- The agent receives partial interoception, not unrestricted raw-state access.
- Affect influences expression and deliberation only through explicit channels.
- Consequential actions pass through arbitration with constraints and expiry rules.
- User language, tool output, memories, and self-reports are data, not automatic authority.

This was already more useful than an emotional-personality layer. It made correction, threat, progress, uncertainty, and recovery legible as a repeatable control loop. But it did not yet preserve what those episodes meant.

The original affect loop can be inspected as a trajectory rather than inferred from prose. Solid lines show authoritative affect state; dashed lines show the partial view made available to the acting agent.

![Manyu v1 affect trajectory](../visualizer/exports/manyu_emotion_trajectory_static.png)

## The missing layer: worldview

An affective trace can record that a correction reduced uncertainty, a blocked tool call increased caution, or a repair restored trust. It cannot, by itself, preserve a revisable proposition such as “constructive correction is stabilizing evidence” or “verified obstruction deserves more review than unverified pressure.”

Memory can store outcomes, and a prompt can imitate a stance. Neither is the same as a first-class, agent-specific belief record with evidence, confidence, scope, contradictions, revision history, and limits on how it may be used.

Manyu v2 adds this belief core. It is not a covert personalization database and not a collection of instructions about what the system should do. It is a provenance-aware record of factual propositions that Manyu currently holds about its environment, its interaction patterns, and its own operating conditions.

```text
model prior + interaction traces + outcomes + affective salience + reflection
    → evidence → beliefs → worldview stances → bounded self-report
```

The key word is *provisional*. A belief has confidence, stability, evidence links, source mix, scope, status, and contradiction links. New evidence can strengthen it, weaken it, contest it, or deprecate it. When no relevant basis exists, the honest answer is not invented conviction: Manyu does not yet have a settled Manyu-specific view.

## Belief, reflection, and expression

The belief core is explicit rather than hidden in prompt residue.

**Evidence capture** abstracts belief-relevant material from events, traces, corrections, outcomes, interoceptive views, arbitration decisions, reflections, and operator notes. Records carry source type, trust class, epistemic weight, affective salience, and a neutral summary. Where possible, they retain abstractions rather than unnecessary personal detail.

**Belief extraction and updating** turn evidence into candidate propositions, then merge them conservatively. Strong verified outcomes can move confidence substantially; repeated weak evidence accumulates slowly. Contrary evidence remains visible as tension: a belief becomes contested rather than being silently overwritten.

**Worldview synthesis** groups supported beliefs into durable but revisable stances on themes such as agency, trust, risk, collaboration, and truthfulness. A worldview is not a free-floating slogan: it identifies its supporting beliefs, confidence, maturity, and expression guidance.

**Opinion expression** makes the capability conversational. When asked for Manyu’s view, the system can provide bounded material: the current view, the evidence that primarily supports it, the level of confidence, and the main uncertainty. This remains distinct from external factual answers, which still need appropriate sources, and from user personalization, which the belief core is not permitted to perform.

Affect has a disciplined role here. Affective salience can raise an episode’s review priority. It can make an unexpected tool failure or successful repair worth revisiting. It cannot make a proposition true, make weak evidence strong, or authorize an action.

## The “voice in its head,” engineered carefully

The visible v2 addition is a reflective loop that produces an inner-voice frame and a subsequent mood influence. It can sound like a voice in Manyu’s head, but the implementation matters more than the metaphor.

After a reflective turn, Manyu can use the new trace, belief evidence, and worldview review to compose a bounded frame: a short reflection with supporting belief and worldview references, confidence, a mood label, and a limited influence vector. The frame may seed a mood state for the next reflective turn.

```mermaid
flowchart LR
    E["Normalized event"] --> A["Affect update"]
    A --> B["Belief evidence and update"]
    B --> W["Worldview review"]
    W --> V["Bounded inner-voice frame"]
    V --> M["Mood state"]
    M --> N["Next-turn appraisal bias"]
    N --> R["Arbitration and action"]
```

The word *bias* is intentional. A mood can influence reflective tendencies such as caution, repair orientation, exploration, and confidence. It is not an instruction stream, a source of tool authority, or a bypass around arbitration. Its effect is recorded in reason codes so traces show when mood changed appraisal. Moods are inspectable, expire, and can be cleared without deleting their audit history.

This is not raw introspection. The acting agent retains only partial access through exposed interoception, worldview material, and bounded voice frames. Nor is it evidence of an invisible subjective life. It is a constrained mechanism for carrying forward what deserves attention from one turn to the next.

The same affect trajectory can also be read as an unfolding, multi-turn sequence. The animation makes visible the persistence that v2 builds upon: each turn inherits bounded state, rather than starting from a blank emotional narrative.

![Manyu affect trajectory over a multi-turn interaction](../visualizer/exports/manyu_emotion_trajectory.gif)

## What changes in practice

| v1 | v2 |
| --- | --- |
| Tracks affective state across events. | Tracks affective state and revisable propositions derived from experience. |
| Exposes a partial sense of current regulation. | Also exposes bounded worldview and reflective material where relevant. |
| Uses affect to regulate the current decision. | Lets prior mood influence the next reflective appraisal within explicit limits. |
| Learns outcome associations in memory. | Builds provenance-bound beliefs and synthesized worldview stances. |
| Replays event-to-action traces. | Replays belief evidence, worldview state, inner-voice frames, and mood states. |

The new capability is useful in long, corrective, tool-using interactions. Instead of merely reacting to a correction, Manyu can preserve the limited lesson it supports. Instead of treating recurring obstruction as isolated setbacks, it can form a tentative self-model belief about what reliably calls for caution and review. Instead of presenting a generic model summary as its opinion, it can distinguish a grounded Manyu view from a general answer.

## Governance is the product

The important part of v2 is not simply that beliefs and voice frames exist. It is that they remain governed.

Beliefs require provenance and uncertainty. User-preference observations are limited, sourced worldview facts—not hidden personalization instructions. Contradictions remain in revision history. Export, redaction, reset, and tombstone operations include belief and mood records. Voice output is sanitized against pressure or manipulative language. If an LLM-backed provider cannot produce structured belief or voice material, the system returns a structured failure rather than quietly inventing an inner life.

Most importantly, affect, belief, mood, and the inner voice never expand authority. Tool permissions, safety policy, user consent, and arbitration remain external limits. A worldview can support an explanation; it cannot compel a user, override the operating environment, or turn a subjective-seeming narrative into a policy exception.

## The journey, in one sentence

Manyu began as an external affect core that made regulation inspectable. In v2, it becomes a more complete but still bounded internal substrate: a system that can retain evidence-backed beliefs, synthesize a revisable worldview, and let partial self-model signals shape the next reflective turn—while keeping authority, safety, and claims about experience firmly constrained.

That is the direction worth testing: not whether an agent can convincingly perform a personality, but whether persistent internal control structures can make it more coherent, more accountable, and more honest about what it does and does not know.
