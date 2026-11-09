---
name: currency-chain-v2
description: Use when a question asks to convert an amount through a sequence of
  currencies using a list of exchange rates, possibly with a fee on each conversion.
  Not for single-rate lookups or non-currency units.
---

# Currency chain conversions

The exchange rates in the prompt are the only truth. They are often unrealistic
(for example 1 JPY = 1.5 EUR). Never use your knowledge of real exchange rates.

## Procedure
1. List the route as legs, for example CHF -> USD, USD -> GBP.
2. For every leg, first quote the rate line from the prompt, word for word, and then
   write the factor:
   - the prompt says "1 CHF = 1.539 USD", so CHF -> USD is multiply by 1.539.
   Every leg of the route is stated in the route direction ("1 FROM = r TO"),
   so every leg is a multiplication by r. Do not divide by a rate.
3. Ignore rates for pairs that are not on the route. They are distractors.
4. If each conversion has a fee of f%, multiply by (1 - f/100) after every leg.
5. Build one expression covering all legs and compute it with the calculator tool.
   Do not round intermediate values, and do not compute any leg in your head.

## Worked example
Prompt: "You hold 1000 JPY. 1 JPY = 1.5 EUR. 1 EUR = 0.8 GBP. 1 USD = 2 EUR.
Route JPY -> EUR -> GBP. Each conversion has a 1% fee."

- JPY -> EUR: the prompt says "1 JPY = 1.5 EUR", so multiply by 1.5, then by 0.99.
  (1.5 EUR per JPY is unrealistic, but it is what the prompt says.)
- EUR -> GBP: the prompt says "1 EUR = 0.8 GBP", so multiply by 0.8, then by 0.99.
- "1 USD = 2 EUR" is not on the route, so ignore it.
- Expression: 1000 * 1.5 * 0.99 * 0.8 * 0.99 = 1176.12

## Output
For each leg, the quoted rate line and the factor; then the expression and the answer.
