# Model Card: Feelz depression-language classifier

This card covers the depression-language detector (the "Language Patterns" mode).
The polarity/sentiment mode uses NLTK's VADER lexicon directly and isn't a
trained model, so it isn't covered here.

## Two models, on purpose

Feelz ships two versions of the same classifier so the improvement is
measurable, not just claimed.

| | V1 - hand-rolled TF-IDF/Naive Bayes | V2 - TF-IDF + Logistic Regression (shipped) |
|---|---|---|
| Code | `Extensions/DepressionScore.py::TweetClassifier` | `Extensions/DepressionScore.py::build_pipeline` |
| Status | Kept only as the baseline V2 is measured against | What the app actually calls (`predict_depressive`) |
| Accuracy | 85.7% | 99.2% |
| Precision | 0.896 | 0.991 |
| Recall | 0.408 | 0.974 |
| F1 | 0.561 | 0.983 |

Stratified 80/20 split, fixed seed (42), 8,251 train / 2,063 held-out test
tweets (22.4% depressive in the test set). Full numbers and confusion
matrices: [`Depression Model/results/metrics.md`](Depression%20Model/results/metrics.md),
reproducible by running `python evaluate_depression_model.py`.

A majority-class baseline (always guess "not depressive") already scores
77.6% accuracy on this data - which is why V1's 85.7% is a weak result even
though it sounds high: it's only a few points above doing nothing, and its
0.41 recall means it misses roughly 6 in 10 tweets actually labeled
depressive. V2 fixes two concrete bugs, not just "a better algorithm":

1. **A silent tokenizer bug.** `process_message()` defaults to `gram=2`
   (bigrams) and returns early *before* the stopword-removal/stemming steps
   ever run - so V1 was trained and shipped on raw, unstemmed bigrams despite
   being documented as doing more. `tokenize_unigrams()` restores the
   preprocessing that was supposed to happen.
2. **No class-imbalance handling.** The dataset is ~78% non-depressive; V1's
   Naive Bayes has no mechanism to correct for that skew, which is most of
   why its recall is so low. V2 uses `class_weight="balanced"` in
   `LogisticRegression`.

## What the numbers don't mean

99.2% accuracy is a measurement of fit to this dataset, not of real-world
diagnostic validity, and that distinction matters more than usual here:

- `Depression Model/sentiment_tweets3.csv` was almost certainly built by
  scraping tweets containing depression-related keywords/hashtags for the
  positive class. That makes the literal presence of words like *"depress-"*
  a strong lexical shortcut for the model, e.g. *"My depression will not let
  me work out"* scores confidently depressive, while *"Extreme sadness, lack
  of energy, hopelessness"* - which describes the same thing without the
  keyword - does not.
- The label is "contains depression-associated language," not "this person
  has clinical depression." A model that's very good at the first task can
  still be a bad instrument for the second.
- Held-out accuracy this high on a single, narrow-domain, English-only,
  Twitter-scraped dataset says nothing about how the model behaves on other
  platforms, other registers of language, sarcasm, or languages other than
  English.

This is why the app frames every result as "linguistic markers associated
with depressive language," never a diagnosis, and why a high-confidence
depressive result surfaces crisis-line information (see
[PRIVACY.md](PRIVACY.md) and the in-app resource panel) instead of a bare
verdict.

## Confidence

`DepressionScore.predict_depressive_with_confidence()` exposes
`LogisticRegression.predict_proba`, so the app shows a confidence percentage
alongside the label instead of a bare boolean, and flags predictions below
65% as low-confidence rather than presenting every result with equal
certainty.

## Reproducing the numbers

```bash
pip install -r requirements.txt -r requirements-eval.txt
python evaluate_depression_model.py
```

This regenerates `Depression Model/results/metrics.json`, `metrics.md`, and
the three confusion-matrix PNGs, then refits V2 on the full dataset and
overwrites `Extensions/Models/depression_pipeline.pickle` - the same
artifact the app loads at runtime.
