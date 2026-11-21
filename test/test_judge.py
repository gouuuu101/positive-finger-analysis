"""判定のテスト。形態素解析器(janome)が無くても動くよう、分かち書きの結果を手で書いている。
実行: python -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import positive_judge as pj  # noqa: E402


def T(*items):
    """"表記|基本形|品詞" の並びからトークンのリストを作る"""
    return [tuple(i.split("|")) for i in items]


def make_polarity():
    pol, _ = pj.build_lexicon({"期待": 1, "がっかり": -1, "友達": 1, "会える": 1, "助かる": 1,
                               "うんざり": -1, "気持ちいい": 1, "サービス": 1})
    return pol


def event(words):
    ws = words.split()
    return (words, frozenset(ws))


class BasicJudgeTests(unittest.TestCase):
    """これまでに確認した判定(否定・二重否定・逆接・混在)が変わっていないこと"""

    def check(self, tokens, expected):
        label, _total, _hits = pj.judge(tokens, make_polarity())
        self.assertTrue(label.startswith(expected), f"{label} != {expected}")

    def test_basic(self):
        self.check(T("楽しかっ|楽しい|形容詞", "た|た|助動詞"), "ポジティブ")
        self.check(T("悲しく|悲しい|形容詞", "なかっ|ない|助動詞", "た|た|助動詞"), "ポジティブ")
        self.check(T("最悪|最悪|名詞", "の|の|助詞", "一日|一日|名詞"), "ネガティブ")
        self.check(T("今日|今日|名詞", "は|は|助詞", "雨|雨|名詞"), "判定不能")

    def test_hedged_and_double_negation(self):
        self.check(T("楽しい|楽しい|形容詞", "と|と|助詞", "は|は|助詞", "言え|言える|動詞",
                     "なかっ|ない|助動詞", "た|た|助動詞"), "ネガティブ")
        self.check(T("嬉しく|嬉しい|形容詞", "ない|ない|助動詞", "わけ|わけ|名詞", "で|で|助動詞",
                     "は|は|助詞", "ない|ない|助動詞"), "ポジティブ")

    def test_contrast(self):
        self.check(T("期待|期待|名詞", "のに|のに|助詞", "がっかり|がっかり|名詞"), "ネガティブ")
        self.check(T("疲れ|疲れる|動詞", "た|た|助動詞", "けど|けど|助詞", "、|、|記号",
                     "楽しい|楽しい|形容詞"), "ポジティブ")


# 「一人で文化祭まわるの確定しました。ありがとう!」(論文の冒頭の例)
CULTURE_FESTIVAL = T("一人|一人|名詞", "で|で|助詞", "文化祭|文化祭|名詞", "まわる|まわる|動詞", "の|の|助詞",
                     "確定|確定|名詞", "し|する|動詞", "まし|ます|助動詞", "た|た|助動詞", "。|。|記号",
                     "ありがとう|ありがとう|感動詞", "!|!|記号")


class SarcasmTests(unittest.TestCase):
    def setUp(self):
        self.pol = make_polarity()
        self.events = [event("一人 文化祭 まわる 確定"), event("待ち時間 長い")]

    def check(self, tokens, mode="flag", events=None, threshold=0.7):
        """report() と同じ流れで、皮肉の判定を含む結果のラベルを返す"""
        label, total, hits = pj.judge(tokens, self.pol)
        if mode != "off" and total >= 0:
            ok, reasons = pj.check_sarcasm(tokens, hits, self.events if events is None else events, threshold)
            if ok:
                return ("ネガティブ(皮肉の可能性)" if mode == "negative" else "皮肉の可能性あり"), reasons
        return label, []

    def test_paper_example_is_flagged_not_positive(self):
        label, reasons = self.check(CULTURE_FESTIVAL)
        self.assertEqual(label, "皮肉の可能性あり")
        self.assertTrue(any("類似度" in r for r in reasons))

    def test_surface_is_positive_without_detection(self):
        label, _ = self.check(CULTURE_FESTIVAL, mode="off")
        self.assertEqual(label, "ポジティブ")

    def test_negative_mode(self):
        label, _ = self.check(CULTURE_FESTIVAL, mode="negative")
        self.assertEqual(label, "ネガティブ(皮肉の可能性)")

    def test_genuine_thanks_is_not_flagged(self):
        genuine = T("友達|友達|名詞", "と|と|助詞", "文化祭|文化祭|名詞", "を|を|助詞", "まわれ|まわれる|動詞",
                    "て|て|助詞", "、|、|記号", "ありがとう|ありがとう|感動詞")
        label, _ = self.check(genuine)
        self.assertEqual(label, "ポジティブ")

    def test_explicit_marker(self):
        tokens = T("ありがとう|ありがとう|感動詞", "(|(|記号", "皮肉|皮肉|名詞", ")|)|記号")
        label, reasons = self.check(tokens, events=[])
        self.assertEqual(label, "皮肉の可能性あり")
        self.assertTrue(any("皮肉" in r for r in reasons))

    def test_negative_text_is_left_alone(self):
        tokens = T("最悪|最悪|名詞", "の|の|助詞", "待ち時間|待ち時間|名詞", "が|が|助詞", "長い|長い|形容詞")
        label, reasons = self.check(tokens)
        self.assertEqual(label, "ネガティブ")
        self.assertEqual(reasons, [])

    def test_single_word_overlap_is_not_enough(self):
        tokens = T("待ち時間|待ち時間|名詞", "に|に|助詞", "感謝|感謝|名詞")
        sim, _ = pj.event_similarity(tokens, self.events)
        self.assertEqual(sim, 0.0)

    def test_threshold(self):
        # 4語の出来事のうち、3語が重なる → 0.75。しきい値 0.8 では疑わない
        tokens = T("一人|一人|名詞", "文化祭|文化祭|名詞", "まわる|まわる|動詞", "ありがとう|ありがとう|感動詞")
        self.assertEqual(self.check(tokens, threshold=0.7)[0], "皮肉の可能性あり")
        self.assertEqual(self.check(tokens, threshold=0.8)[0], "ポジティブ")


class EventLearningTests(unittest.TestCase):
    def setUp(self):
        self.pol = make_polarity()

    def test_extracts_event_before_connective(self):
        # 待ち時間が長くて疲れた → 出来事「待ち時間 長い」
        tokens = T("待ち時間|待ち時間|名詞", "が|が|助詞", "長く|長い|形容詞", "て|て|助詞",
                   "疲れ|疲れる|動詞", "た|た|助動詞")
        self.assertEqual(pj.extract_events(tokens, self.pol), [["待ち時間", "長い"]])

    def test_pair_connective(self):
        # 電車に乗り遅れたのが悲しい
        tokens = T("電車|電車|名詞", "に|に|助詞", "乗り遅れ|乗り遅れる|動詞", "た|た|助動詞",
                   "の|の|助詞", "が|が|助詞", "悲しい|悲しい|形容詞")
        self.assertEqual(pj.extract_events(tokens, self.pol), [["電車", "乗り遅れる"]])

    def test_negated_emotion_is_excluded(self):
        # 待ち時間が長くて疲れなかった → 感情表現が否定されているので除く(論文と同じ)
        tokens = T("待ち時間|待ち時間|名詞", "が|が|助詞", "長く|長い|形容詞", "て|て|助詞",
                   "疲れ|疲れる|動詞", "なかっ|ない|助動詞", "た|た|助動詞")
        self.assertEqual(pj.extract_events(tokens, self.pol), [])

    def test_positive_emotion_is_excluded(self):
        tokens = T("友達|友達|名詞", "に|に|助詞", "会え|会える|動詞", "て|て|助詞", "嬉しかっ|嬉しい|形容詞")
        self.assertEqual(pj.extract_events(tokens, self.pol), [])

    def test_negation_is_kept_in_event(self):
        tokens = T("仕事|仕事|名詞", "が|が|助詞", "終わら|終わる|動詞", "ない|ない|助動詞", "ので|ので|助詞",
                   "困る|困る|動詞")
        self.assertEqual(pj.extract_events(tokens, self.pol), [["仕事", "終わる", "ない"]])


if __name__ == "__main__":
    unittest.main()
