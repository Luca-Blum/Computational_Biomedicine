from pathlib import Path
from unittest import TestCase

import numpy as np
from sklearn.dummy import DummyClassifier

from idiva.clf.df import get_clinvar_clf_data
from idiva.clf.utils import get_train_test
from idiva.clf2.classifier import Classifier

BASE = (Path(__file__).parent) / "data_for_tests/large_head"

PATHS = {
    'ctrl': BASE / "control_v2.vcf",
    'case': BASE / "case_processed_v2.vcf",
    'clinvar_clf_data': BASE / 'clinvar_clf_data.csv'
}


def get_datasets():
    clinvar_clf_data = get_clinvar_clf_data(BASE)
    train_data, train_labels, eval_data, eval_labels = get_train_test(clinvar_clf_data)
    return train_data, train_labels, eval_data, eval_labels


class TestClf(TestCase):
    def test_dummy_classifier(self):
        dummy_clf = DummyClassifier(strategy="most_frequent")
        train_data, train_labels, eval_data, eval_labels = get_datasets()

        dummy_clf.fit(train_data, train_labels)
        dummy_clf.predict(train_data)
        score = dummy_clf.score(train_data, train_labels)
        self.assertEqual(0.5, np.round(score, 1))

    def test_grid_search(self):
        cv = Classifier()
        cv.create_model(n_steps=1, epochs=1)
        cv.x = cv.x[:10]
        cv.labels = cv.labels[:10]
        cv.train(cv.x, cv.labels)
        print(cv.model.cv_results_)
