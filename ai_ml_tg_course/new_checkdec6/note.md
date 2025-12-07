# Day - Dec 6, 2025 - Statistices - Hypothesis testing 1

# Hypothesis testing
Hypothesis testing is a method in inferential statistics that helps make conclusions about a population using data from a sample.  

## Key ideas

- A population is the entire group of interest; a sample is the subset of that group that is actually observed or measured.  
- Because observing the whole population is usually impractical, hypothesis testing uses the sample to judge whether a belief (hypothesis) about the population is reasonable.  

## What a hypothesis test does

- A statistical hypothesis test is a formal procedure for deciding whether the data at hand provide enough evidence to support a particular hypothesis about a population parameter (such as a mean or proportion).  
- The result is probabilistic: it does not prove a hypothesis, but it quantifies how consistent the observed data are with the hypothesis, allowing informed decisions under uncertainty.

## Steps in Hypothesis Testing

1. **State the hypothesis**  
   - Formulate the null hypothesis \(H_0\) and the alternative hypothesis \(H_1\).

2. **Conducting experiment**  
   - Collect sample data using a suitable study design or experiment.

3. **Choosing test statistics**  
   - Select an appropriate statistical test (z-test, t-test, chi-square, etc.) and compute its value.

4. **Decision making**  
   - Compare the test statistic to the critical value or use the p-value to decide whether to reject \(H_0\).

5. **Drawing conclusion about population**  
   - Interpret the decision in the context of the original question and state the conclusion about the population.

flowchart TD
    A["State the hypothesis"] --> B["Conducting experiment"]
    B --> C["Choosing test statistics"]
    C --> D["Decision making"]
    D --> E["Drawing conclusion about population"]


## Types of Hypotheses

1. **Null hypothesis (H0)**  
   - States that there is no significant effect or relationship between the variables being studied.  
   - Serves as the starting point or “no effect” status quo and is assumed true until there is strong evidence against it.  
   - Hypothesis testing gathers data to decide whether to reject H0 in favor of the alternative hypothesis.

2. **Alternative hypothesis (H1 or Ha)**  
   - Contradicts the null hypothesis and states that there is a significant effect or relationship between the variables.  
   - Represents the researcher’s claim or the research hypothesis to be supported with statistical evidence.

## Important points

- Decide which statement will be H0 and which will be Ha (often H0 says “nothing new is happening”).  
- Evidence is collected to try to reject the null hypothesis.  
- Failing to reject H0 does not prove H0 is true; it only means there is not enough evidence for Ha.

## Jury trial analogy

- In a trial, H0 is “the defendant is not guilty” and Ha is “the defendant is guilty.”  
- The jury starts by assuming H0 and only rejects it if the evidence is strong enough (beyond a reasonable doubt) to support Ha.




| Test statistic | Typical null hypothesis example                                               | Typical alternative hypothesis example                                                     | Common tests using it                 |
| -------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------- |
| t‑value        | Mean of group 1 equals mean of group 2                                        | Means of the two groups are not equal                                                      | t‑test, regression test               |
| z‑value        | Mean equals a specified population mean or another group mean                 | Mean is different from the specified value or other group mean                             | z‑test, large‑sample proportion tests |
| F‑value        | All group means are equal (or between‑group variance ≈ within‑group variance) | At least one group mean differs (between‑group variance larger than within‑group variance) | ANOVA, ANCOVA, MANOVA                 |



