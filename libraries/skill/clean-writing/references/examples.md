# Clean Writing Examples

These examples teach transformations, not fixed phrases. Do not imitate wording mechanically.

## 1. Process history → current state

**Before**

> We initially considered allowing users to configure a custom execution order, but after several rounds of discussion we felt the interaction was too complex for the target user, so the first release will temporarily focus on fixed defaults.

**After**

> The first release supports fixed default ordering. User-configured execution order is out of scope.

**Principle**: State the current capability and boundary. Remove the internal decision path.

## 2. Defensive evidence → product behavior

**Before**

> Based on extensive benchmarking of mature products, the capability has already been sufficiently validated in the market, which provides strong evidence for adopting a similar approach.

**After**

> Users can adjust the output with a single control.

**Principle**: Evidence used for internal confidence does not automatically belong in the product description.

## 3. Evidence central to a decision → concise evidence

**Before**

> We investigated a number of comparable products and found that many of them use a lightweight interaction, which, in our view, suggests that reducing friction could be meaningful in active scenarios.

**After**

> Comparable products use a lightweight interaction that reduces friction during active use. This supports keeping the interaction in the primary set.

**Principle**: When evidence changes the decision, show the evidence and decision without narrating the research effort.

## 4. Reasoning trace → system relationship

**Before**

> Because the input has both slow drift and fast noise, and because a single filter cannot fully handle both, the system therefore needs to combine coarse correction, a second-stage filter, and final smoothing.

**After**

> Output stabilization combines coarse correction, a second-stage filter, and final smoothing.

**Principle**: In a product definition, describe the architecture. Put detailed rationale elsewhere unless the reader needs it.

## 5. Necessary rationale stays

**Before**

> The component uses a wider tolerance range.

**After**

> The component keeps a wider tolerance range at close distances so readings remain stable during rapid change.

**Principle**: Do not delete rationale that explains a non-obvious design requirement.

## 6. Audit language → material boundary

**Before**

> Current evidence is not yet sufficient to fully prove that the system can maintain the target rate under all conditions, and more validation is required in subsequent testing.

**After**

> The target rate is validated on the current test configuration; behavior under other conditions remains unverified.

**Principle**: Replace audit bookkeeping with the boundary the reader needs.

## 7. Hedging stack → calibrated uncertainty

**Before**

> This approach may potentially be able to improve the stability of the result in some scenarios.

**After**

> This approach may improve stability in low-noise scenarios; it has not been validated under high load.

**Principle**: Keep uncertainty precise. Remove vague stacked hedges.

## 8. Noun-heavy prose → direct verb

**Before**

> The system performs an analysis of the input and provides a selection of an appropriate action.

**After**

> The system analyzes the input and selects an action.

**Principle**: Prefer direct verbs.

## 9. Marketing adjective → observable property

**Before**

> The product delivers a seamless and powerful experience.

**After**

> The product keeps the selected target in view while adjusting its path around obstacles.

**Principle**: Show behavior instead of claiming quality.

## 10. Fragmented prose → table

**Before**

> Maximum rate is 5 units/s.
>
> Acceleration target is 2 units/s².
>
> Maximum angle is 15°.
>
> Target weight is 3 kg class.

**After**

| Item | Target |
|---|---:|
| Maximum rate | 5 units/s |
| Acceleration | 2 units/s² |
| Maximum angle | 15° |
| Weight | 3 kg class |

**Principle**: Parallel parameters belong in a structure that supports scanning.

## 11. Author meta → direct content

**Before**

> This section mainly explains how the sensing module allows the system to understand where it can safely go.

**After**

> The sensing system identifies traversable areas and obstacles around the system.

**Principle**: Describe the subject, not what the writer intends to describe.

## 12. Fake completeness → delete

**Before**

> Looking ahead, there are also opportunities to explore broader ecosystem integration, richer capabilities, and more diversified use cases.

**After**

> [Delete unless specific future work is part of the artifact.]

**Principle**: Do not add generic future directions to make a document feel complete.

## 13. Status history stays when change is the subject

**Before**

> The previous build used the standard channel. This week we replaced it with the low-latency channel after load tests showed repeated drops.

**After (Status mode)**

> **Changed:** replaced the standard channel with the low-latency channel after load tests showed repeated drops.

**Principle**: Change history is useful in a status report; compress it to the change and reason.

## 14. Research process → finding

**Before**

> We searched product pages, reviews, forums, and several demonstrations, and after cross-checking the available materials we did not find evidence that the mechanism physically rotates 90 degrees.

**After (Research mode)**

> Available product documentation and demonstrations do not establish a 90° physical rotation mechanism.

**Principle**: Report the evidence state, not the browsing diary.

## 15. Executive answer → decision first

**Before**

> There are several factors to consider, including development complexity, user learning cost, target audience, and the narrow value of advanced configuration. After weighing these factors, it may be better not to include it in the first release.

**After**

> Do not include advanced configuration in the first release. Its development and learning costs outweigh the expected value for the target user.

**Principle**: In executive/decision language, lead with the decision and retain only decisive rationale.
