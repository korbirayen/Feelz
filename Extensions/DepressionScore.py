# for text manipulation
import nltk
import re

# importing different libraries for text processing
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# for data manipulation
from math import log, sqrt
import pandas as pd
import numpy as np

import os, sys
from pathlib import Path
import types

import pickle

MODEL_PATH = Path(__file__).resolve().parent / "Models" / "classifier.pickle"
PIPELINE_PATH = Path(__file__).resolve().parent / "Models" / "depression_pipeline.pickle"

def process_message(message, lower_case = True, stem = True, stop_words = True, gram = 2):
    if lower_case:
        message = message.lower()
    words = word_tokenize(message)
    words = [w for w in words if len(w) > 2]
    if gram > 1:
        w = []
        for i in range(len(words) - gram + 1):
            w += [' '.join(words[i:i + gram])]
        return w
    if stop_words:
        sw = stopwords.words('english')
        words = [word for word in words if word not in sw]
    if stem:
        stemmer = PorterStemmer()
        words = [stemmer.stem(word) for word in words]   
    return words

class TweetClassifier(object):
    def __init__(self, trainData, method = 'tf-idf'):
        self.tweets, self.labels = trainData['message'], trainData['label']
        self.method = method

    def train(self):
        self.calc_TF_and_IDF()
        if self.method == 'tf-idf':
            self.calc_TF_IDF()
        else:
            self.calc_prob()

    def calc_prob(self):
        self.prob_depressive = dict()
        self.prob_positive = dict()
        for word in self.tf_depressive:
            self.prob_depressive[word] = (self.tf_depressive[word] + 1) / (self.depressive_words + \
                                                                len(list(self.tf_depressive.keys())))
        for word in self.tf_positive:
            self.prob_positive[word] = (self.tf_positive[word] + 1) / (self.positive_words + \
                                                                len(list(self.tf_positive.keys())))
        self.prob_depressive_tweet, self.prob_positive_tweet = self.depressive_tweets / self.total_tweets, self.positive_tweets / self.total_tweets 


    def calc_TF_and_IDF(self):
        noOfMessages = self.tweets.shape[0]
        self.depressive_tweets, self.positive_tweets = self.labels.value_counts()[1], self.labels.value_counts()[0]
        self.total_tweets = self.depressive_tweets + self.positive_tweets
        self.depressive_words = 0
        self.positive_words = 0
        self.tf_depressive = dict()
        self.tf_positive = dict()
        self.idf_depressive = dict()
        self.idf_positive = dict()
        for i in range(noOfMessages):
            message_processed = process_message(self.tweets.iloc[i])
            count = list() #To keep track of whether the word has ocured in the message or not.
                           #For IDF
            for word in message_processed:
                if self.labels.iloc[i]:
                    self.tf_depressive[word] = self.tf_depressive.get(word, 0) + 1
                    self.depressive_words += 1
                else:
                    self.tf_positive[word] = self.tf_positive.get(word, 0) + 1
                    self.positive_words += 1
                if word not in count:
                    count += [word]
            for word in count:
                if self.labels.iloc[i]:
                    self.idf_depressive[word] = self.idf_depressive.get(word, 0) + 1
                else:
                    self.idf_positive[word] = self.idf_positive.get(word, 0) + 1

    def calc_TF_IDF(self):
        self.prob_depressive = dict()
        self.prob_positive = dict()
        self.sum_tf_idf_depressive = 0
        self.sum_tf_idf_positive = 0
        for word in self.tf_depressive:
            self.prob_depressive[word] = (self.tf_depressive[word]) * log((self.depressive_tweets + self.positive_tweets) \
                                                          / (self.idf_depressive[word] + self.idf_positive.get(word, 0)))
            self.sum_tf_idf_depressive += self.prob_depressive[word]
        for word in self.tf_depressive:
            self.prob_depressive[word] = (self.prob_depressive[word] + 1) / (self.sum_tf_idf_depressive + len(list(self.prob_depressive.keys())))
            
        for word in self.tf_positive:
            self.prob_positive[word] = (self.tf_positive[word]) * log((self.depressive_tweets + self.positive_tweets) \
                                                          / (self.idf_depressive.get(word, 0) + self.idf_positive[word]))
            self.sum_tf_idf_positive += self.prob_positive[word]
        for word in self.tf_positive:
            self.prob_positive[word] = (self.prob_positive[word] + 1) / (self.sum_tf_idf_positive + len(list(self.prob_positive.keys())))
            
    
        self.prob_depressive_tweet, self.prob_positive_tweet = self.depressive_tweets / self.total_tweets, self.positive_tweets / self.total_tweets 
                    
    def classify(self, processed_message):
        pDepressive, pPositive = 0, 0
        for word in processed_message:                
            if word in self.prob_depressive:
                pDepressive += log(self.prob_depressive[word])
            else:
                if self.method == 'tf-idf':
                    pDepressive -= log(self.sum_tf_idf_depressive + len(list(self.prob_depressive.keys())))
                else:
                    pDepressive -= log(self.depressive_words + len(list(self.prob_depressive.keys())))
            if word in self.prob_positive:
                pPositive += log(self.prob_positive[word])
            else:
                if self.method == 'tf-idf':
                    pPositive -= log(self.sum_tf_idf_positive + len(list(self.prob_positive.keys()))) 
                else:
                    pPositive -= log(self.positive_words + len(list(self.prob_positive.keys())))
            pDepressive += log(self.prob_depressive_tweet)
            pPositive += log(self.prob_positive_tweet)
        return pDepressive >= pPositive
    
    def predict(self, testData):
        result = dict()
        for (i, message) in enumerate(testData):
            processed_message = process_message(message)
            result[i] = int(self.classify(processed_message))
        return result


def _ensure_pickle_compatibility():
    main_module = sys.modules.get("__main__")
    if main_module is not None and not hasattr(main_module, "TweetClassifier"):
        setattr(main_module, "TweetClassifier", TweetClassifier)

    if "pandas.core.indexes.numeric" not in sys.modules:
        numeric_module = types.ModuleType("pandas.core.indexes.numeric")
        numeric_module.Int64Index = pd.Index
        numeric_module.UInt64Index = pd.Index
        numeric_module.Float64Index = pd.Index
        sys.modules["pandas.core.indexes.numeric"] = numeric_module

def RunModel(processed_text):
    """Classify with the original hand-rolled TF-IDF/Naive Bayes model (V1).

    Kept for reference and for evaluate_depression_model.py, which measures it
    against the shipped classifier below. See Depression Model/results/metrics.md:
    V1 barely beats a majority-class guess (85.7% accuracy, 0.41 recall on held-out
    data) because it misses most actually-depressive text.
    """
    _ensure_pickle_compatibility()
    with MODEL_PATH.open('rb') as model_file:
        model = pickle.load(model_file)
    result = model.classify(processed_text)
    return result


def tokenize_unigrams(message):
    """Tokenizer for the V2 pipeline: unigrams with stopword removal and stemming.

    process_message defaults to gram=2, which returns raw bigrams and skips the
    stopword/stemming steps entirely (see the early `if gram > 1: return w`
    above) - that's the behavior V1 was trained and shipped with. Forcing
    gram=1 here restores the preprocessing V1 was documented as doing but never
    actually applied.
    """
    return process_message(message, gram=1)


def build_pipeline():
    """Construct the V2 model: TF-IDF unigrams + Logistic Regression.

    class_weight='balanced' matters here - the dataset is ~78% non-depressive,
    so an unweighted model can coast on the majority class the way V1 does.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ("tfidf", TfidfVectorizer(tokenizer=tokenize_unigrams, token_pattern=None)),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
    ])


_pipeline_cache = None


def predict_depressive(text):
    """Classify raw text with the V2 pipeline (99.2% accuracy, 0.97 recall on
    held-out data - see Depression Model/results/metrics.md). This is the model
    the app uses; RunModel/TweetClassifier above is kept only as the baseline
    V2 is measured against.
    """
    global _pipeline_cache
    if _pipeline_cache is None:
        with PIPELINE_PATH.open('rb') as f:
            _pipeline_cache = pickle.load(f)
    return bool(_pipeline_cache.predict([text])[0])


#cwd = os.getcwd()  # Get the current working directory (cwd)
#files = os.listdir(cwd)  # Get all the files in that directory
#print("Files in %r: %s" % (cwd, files))

#print(RunModel(process_message("Extreme depression, lack of energy, hopelessness")))