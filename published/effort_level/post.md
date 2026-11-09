# Do I need all that LLM reasoning?

Have you ever turned up a model’s reasoning effort—not because the task seemed to require it, but because you weren’t confident that a lower setting would deliver an equally good answer? I most certainly have.

That uncertainty motivated me to explore the trade-off: when did additional reasoning improve the answer, and when was I using a sledgehammer to crack a nut? I wanted to build my confidence in choosing lower-effort settings for everyday tasks, based on results I could verify. To investigate, I built a series of experiments around three questions:

1. How much does reasoning improve the results?
2. Is there a point where increasing effort stops being worth it?
3. Can a model with low or no reasoning effort, but access to the right tools, compete with one using more reasoning?

## Designing the experiment

The experiment required problems with independently verifiable answers, so responses could be assessed for correctness rather than how convincing they sounded.

The generated puzzles covered four task families:

- **Dates:** Determine a deadline under specified calendar rules.
- **Currency conversions:** Convert an amount along a specified route using supplied exchange rates.
- **Scheduling:** Determine when all tasks finish, given their durations and execution rules.
- **Tables:** Calculate totals and comparisons from sales records.

Each family had three difficulty variants, designed to add calculation steps or constraints such as holidays, conversion fees, or worker limits. Generating 20 puzzles per variant produced 60 puzzles per family and **240 puzzles in total**.

Each puzzle had a reference answer computed from the stated rules. Responses ended with a standard final-answer line and were graded automatically against that reference. Dates and integer values had to match; monetary answers were accepted within one cent of the reference. This made scoring reproducible under a defined rubric rather than dependent on how persuasive the explanation sounded.

The reasoning comparison used GPT-6 Luna through the Copilot SDK at four effort settings: none, low, medium, and high. Each of the 240 puzzles was attempted once at every setting, producing **960 responses without tools**.

Two further runs repeated the same puzzles with calculator access, at none and low effort, adding **480 responses**. The calculator’s description instructed the model to use it for arithmetic rather than perform calculations itself. Calculator access at medium and high effort was not tested.

The same puzzles were used in all six configurations. Accuracy was the proportion of responses graded correct. Recorded input and output tokens were summed across all model calls needed for each puzzle. Elapsed time covered session creation, the interaction, and session closure. Full final responses were saved for error analysis.

## Reasoning effort: accuracy and trade-offs

Enabling reasoning produced the largest improvement. Accuracy rose from **44% with reasoning disabled to 88% at low effort**, then increased to 94% at medium and 96% at high.

The additional gains became progressively smaller: moving from none to low produced a net 106 more correct answers, low to medium added 15, and medium to high added 5.

| Effort | Accuracy | Average total tokens per puzzle¹ | Mean time |
|---|---:|---:|---:|
| None | 44% | 3,262 | 4.7s |
| Low | 88% | 3,488 | 7.3s |
| Medium | 94% | 3,566 | 8.1s |
| High | 96% | 3,584 | 8.4s |

¹ Total tokens means recorded input plus output tokens.

These are aggregate improvements, not a guarantee that more effort fixes an individual answer. Compared with medium, high answered 13 previously incorrect puzzles correctly, but got eight previously correct puzzles wrong: a net gain of five.

### Where did the additional accuracy come from?

Some task variants offered no room for improvement in this run. The simplest scheduling and table puzzles were already answered perfectly without reasoning.

Other tasks benefited substantially. Currency conversions showed the largest gain from enabling reasoning. Increasing effort also improved accuracy on the most complex conversion tasks:

| Reasoning effort | Correct answers |
|---|---:|
| Low | 8/20 |
| Medium | 14/20 |
| High | 18/20 |

These conversions require more than multiplication. The model must select the relevant rates, preserve their direction, apply fees consistently, and avoid intermediate rounding. Each step introduces another opportunity for error, making additional computation potentially useful for organising and checking the calculation.

### Was higher effort worth the additional resources?

These results show diminishing accuracy gains, but they do **not** establish diminishing value for money. High consumed **2.7% more recorded input-plus-output tokens than low**, while answering 20 more puzzles correctly. From medium to high, total tokens increased by just **0.5%**, alongside five more correct answers.

Why was the token increase so small? Input dominated the total, remaining around 3,300 tokens per puzzle. Output rose from 217 tokens at low to 305 at high—an increase of **41%**, but a relatively small addition to that input. From medium to high, output rose from 277 to 305, or about **10%**. The small increase in total tokens therefore masks a larger proportional increase in generation.

Another way to combine accuracy and usage is **tokens per correct answer**: total tokens across all attempts, including incorrect answers, divided by the number answered correctly. High recorded **3,723 tokens per correct answer**, compared with **3,787 at medium** and **3,968 at low**. Lower is better on this metric, and high had the best observed result. This is an aggregate efficiency measure, not an estimate of tokens spent only on successful answers or the cost of retrying failures.

Neither measure establishes monetary cost. Input, output, and cached input may be priced differently; I did not calculate charges using those rates. A small increase in total tokens does not necessarily mean an equally small increase in price.

Low effort was a capable starting point in this experiment, but high achieved the best aggregate accuracy and the lowest observed tokens per correct answer. Whether the extra correct answers are worth the additional resources still depends on the consequences of an error.

That left another route to investigate: could a calculator recover comparable accuracy with reasoning disabled—and at what token cost per puzzle?

## Can a calculator substitute for reasoning?

A calculator changes how the task is executed. The model still has to interpret the problem and choose the operations, but it can delegate their numerical evaluation.

With reasoning disabled, calculator access raised accuracy from **44% to 74%**. At low effort, the calculator-assisted run reached **92%**, but neither calculator configuration matched high effort without tools.

| Configuration | Accuracy | Average total tokens per puzzle | Mean time |
|---|---:|---:|---:|
| None, no calculator | 44% | 3,262 | 4.7s |
| None + calculator | 74% | 8,962 | 7.8s |
| Low, no calculator | 88% | 3,488 | 7.3s |
| Low + calculator | 92% | 7,492 | 8.5s |
| High, no calculator | 96% | 3,584 | 8.4s |

### Where the calculator helped

Table calculations showed the clearest benefit. Without reasoning, calculator access increased correct answers from **23/60 to 59/60**, matching high effort’s score on this family.

It also helped when reasoning was already enabled. At low effort, the most complex table tasks improved from **12/20 to 18/20**. These tasks required calculating revenue for each region and finding the difference between the top two.

One matched example illustrated the distinction between choosing the comparison and getting the arithmetic right. Both final responses identified the correct top two regions. The response without a calculator overstated one region’s revenue by 3; the calculator-assisted response gave the correct total and final difference.

The simpler table tasks were already answered perfectly at low effort, so calculator access offered no accuracy gain there.

### What calculator access did not resolve

The most complex currency conversions remained problematic: **low effort with a calculator answered 9/20 correctly**, compared with **18/20 at high effort without tools**.

A final response from the no-reasoning calculator run illustrated a different source of error. The supplied rate was: 1 EUR = 1.4736 GBP. The response described dividing by 1.4736 to convert euros into pounds. The stated rate required multiplication. Numerical evaluation cannot make a wrongly chosen operation appropriate for the question.

These examples illustrate errors visible in the saved final responses; they do not establish how frequently each error occurred or reveal the model’s internal reasoning.

Across the full suite, adding the calculator at low effort produced a net nine more correct answers, taking accuracy from 88% to 92%. That net gain included 18 puzzles answered correctly after an incorrect no-tool response, and nine that changed in the opposite direction.

### The resource trade-off

Delegating arithmetic does not eliminate the interaction around it. The model must formulate a calculator request, receive the result, and continue the response. Further model calls process the accumulated conversation, so input tokens are recorded again, including context from the preceding interaction.

The runs without tools recorded one model call per puzzle. With calculator access, the average rose to **2.54 calls with reasoning disabled** and **2.10 at low effort**. Average input consumption reached approximately **8,856 tokens per puzzle** without reasoning and **7,339 at low effort**.

The no-reasoning calculator run generated fewer output tokens—106 per puzzle, versus 153 at low effort—but that saving was outweighed by additional recorded input. Disabling reasoning therefore did not minimise total token consumption in the calculator runs.

Compared with the matching no-tool effort setting, calculator access used **2.75 times as many total tokens at none** and **2.15 times as many at low**. Most of the additional input was recorded as cached input, so these ratios should not be read as increases in monetary cost.

Both calculator configurations consumed more total tokens than high effort without tools. Low effort with the calculator also took approximately the same mean time as high effort alone. On this task set, calculator access matched high-effort accuracy on table calculations, but did not provide comparable accuracy across the suite with fewer recorded tokens.

## What this experiment does not establish

This was one model, 240 synthetic puzzles, and one attempt per puzzle at each configuration. It does not show how repeatable the differences are or establish the best setting for everyday writing, coding, or other tasks. Only two calculator configurations were tested, using a tool that explicitly encouraged arithmetic calls. The elapsed times describe these runs, including session overhead, rather than a controlled comparison of model generation speed. Monetary cost was not established.

## What I take from this

I started hoping lower effort would be enough, and a calculator could close the remaining gap without increasing cost. This experiment did not establish either as a general answer across the suite. Some tasks needed no additional reasoning, but high achieved the best overall accuracy with only a small increase in recorded total tokens over medium. It was harder to dismiss as a sledgehammer than I had expected.

The calculator helped, especially with tables, but more than doubled recorded tokens at both tested effort settings without matching high overall. It was not the low-token substitute for reasoning I had hoped for; whether it was financially cheaper remains unanswered.

These results leave me more confident in both medium and high, for different reasons. Medium performed well on these puzzles with slightly fewer tokens, reassuring me that I do not always need the highest setting. High achieved better accuracy without a large increase in total recorded tokens, making me more comfortable choosing it when accuracy takes priority. I now have less reason to treat medium as an uncertain compromise, or high as automatically excessive.
