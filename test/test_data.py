import csv
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "sarcasm_eval.csv")


class DataIntegrity(unittest.TestCase):
    def setUp(self):
        with open(DATA, encoding="utf-8-sig", newline="") as fh:
            self.rows = list(csv.DictReader(fh))

    def test_columns_and_labels(self):
        self.assertEqual(list(self.rows[0].keys()), ["id", "text", "label", "category", "kind", "split"])
        for r in self.rows:
            self.assertIn(r["label"], ("皮肉", "皮肉でない"))
            self.assertIn(r["split"], ("dev", "test"))
            self.assertTrue(r["text"].strip())

    def test_unique_and_balanced(self):
        texts = [r["text"] for r in self.rows]
        self.assertEqual(len(texts), len(set(texts)), "重複した文がある")
        ids = [r["id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sum(r["label"] == "皮肉" for r in self.rows), len(self.rows) // 2)

    def test_both_splits_have_both_labels(self):
        for sp in ("dev", "test"):
            labels = {r["label"] for r in self.rows if r["split"] == sp}
            self.assertEqual(labels, {"皮肉", "皮肉でない"})


if __name__ == "__main__":
    unittest.main()
