# Depression-language classifier evaluation

Stratified 80/20 split, seed=42, 8251 train / 2063 test tweets (22.4% depressive in test set).

| model | accuracy | precision | recall | f1 |
|---|---|---|---|---|
| Majority baseline | 0.776 | 0.000 | 0.000 | 0.000 |
| Hand-rolled TF-IDF NB | 0.857 | 0.896 | 0.408 | 0.561 |
| TF-IDF + LogReg | 0.992 | 0.991 | 0.974 | 0.983 |

## Limitations

- The majority baseline (77.6% accuracy) shows why accuracy alone is misleading here: the hand-rolled TF-IDF/Naive Bayes model's 85.7% accuracy is only a few points above always guessing 'not depressive', and its 0.41 recall means it misses most tweets actually labeled depressive. The TF-IDF + Logistic Regression model fixes both the class-imbalance handling and a tokenizer bug (see `tokenize_unigrams` in Extensions/DepressionScore.py).
- Both models were trained on `sentiment_tweets3.csv`, which was almost certainly built by scraping tweets containing depression-related keywords/hashtags for the positive class. That makes the literal presence of words like 'depress-' a very strong lexical shortcut - e.g. 'My depression will not let me work out' scores confidently depressive, while 'Extreme sadness, lack of energy, hopelessness' (no literal keyword) does not. High held-out accuracy here measures fit to this dataset's collection method, not real-world diagnostic validity - hence the app frames results as 'linguistic markers', never a diagnosis.
