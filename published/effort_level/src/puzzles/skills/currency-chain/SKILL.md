---
name: currency-chain
description: Use when a question asks to convert an amount through a sequence of
  currencies using a list of exchange rates, possibly with a fee on each conversion.
  Not for single-rate lookups or non-currency units.
---

# Currency chain conversions

## Procedure
1. Write the route as a list of legs, for example CHF -> USD -> GBP.
2. For each leg, find its rate in the prompt. Rates are stated as "1 X = r Y".
   To convert X into Y, multiply by r. If only the reverse is stated ("1 Y = r X"),
   divide by r.
3. Ignore rates for pairs that are not on the route. They are distractors.
4. If a fee of f% applies to each conversion, multiply by (1 - f/100) after every leg,
   not once at the end.
5. Build one expression covering all legs and compute it with the calculator tool.
   Do not round intermediate values, and do not compute any leg in your head.
6. Use the rates exactly as given. Do not "correct" a rate because it looks unrealistic.

## Output
List each leg with the rate used, show the final expression, then give the answer.
