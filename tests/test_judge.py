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


class ContrastRuleTests(unittest.TestCase):
    """「ネガティブな出来事のあとにポジティブな節」というルール(鈴木 修士論文の考え方の簡易版)"""

    def pol(self):
        pol, _ = pj.build_lexicon({"最高": 1, "嬉しい": 1, "うるさい": -1, "遅れる": -1, "疲れる": -1, "おいしい": 1})
        return pol

    def test_sarcasm_sentence_break(self):
        # 電車が遅れた。最高だね。 → 皮肉の可能性
        toks = T("電車|電車|名詞", "が|が|助詞", "遅れ|遅れる|動詞", "た|た|助動詞", "。|。|記号",
                 "最高|最高|名詞", "だ|だ|助動詞", "ね|ね|助詞", "。|。|記号")
        self.assertIsNotNone(pj.contrast_sarcasm(toks, self.pol()))

    def test_sarcasm_comma(self):
        toks = T("隣|隣|名詞", "が|が|助詞", "うるさい|うるさい|形容詞", "、|、|記号", "最高|最高|名詞", "だ|だ|助動詞")
        self.assertIsNotNone(pj.contrast_sarcasm(toks, self.pol()))

    def test_genuine_after_hardship_with_concessive(self):
        # 待ち時間は疲れたけど、おいしかった → 本物の肯定(逆接)
        toks = T("疲れ|疲れる|動詞", "た|た|助動詞", "けど|けど|助詞", "、|、|記号", "おいしかっ|おいしい|形容詞", "た|た|助動詞")
        self.assertIsNone(pj.contrast_sarcasm(toks, self.pol()))

    def test_genuine_after_hardship_with_sentence_start_conjunction(self):
        toks = T("疲れ|疲れる|動詞", "た|た|助動詞", "。|。|記号", "でも|でも|接続詞", "、|、|記号", "嬉しい|嬉しい|形容詞")
        self.assertIsNone(pj.contrast_sarcasm(toks, self.pol()))

    def test_positive_only_and_negative_only(self):
        self.assertIsNone(pj.contrast_sarcasm(T("嬉しい|嬉しい|形容詞", "。|。|記号"), self.pol()))
        self.assertIsNone(pj.contrast_sarcasm(T("疲れ|疲れる|動詞", "た|た|助動詞", "。|。|記号"), self.pol()))

    def test_negated_positive_is_not_positive(self):
        # うるさい。嬉しくない。 → 後ろは否定されているのでポジティブではない
        toks = T("うるさい|うるさい|形容詞", "。|。|記号", "嬉しく|嬉しい|形容詞", "ない|ない|助動詞", "。|。|記号")
        self.assertIsNone(pj.contrast_sarcasm(toks, self.pol()))

    def test_event_database_marks_negative_clause(self):
        # 辞書にない出来事でも、見本と似ていればネガティブな節になる
        toks = T("傘|傘|名詞", "を|を|助詞", "忘れ|忘れる|動詞", "た|た|助動詞", "。|。|記号",
                 "最高|最高|名詞", "だ|だ|助動詞", "。|。|記号")
        ev = [event("傘 忘れる")]
        self.assertIsNone(pj.contrast_sarcasm(toks, self.pol()))
        self.assertIsNotNone(pj.contrast_sarcasm(toks, self.pol(), ev))

    def test_check_sarcasm_uses_rule(self):
        toks = T("電車|電車|名詞", "が|が|助詞", "遅れ|遅れる|動詞", "た|た|助動詞", "。|。|記号", "最高|最高|名詞")
        pol = self.pol()
        _l, _t, hits = pj.judge(toks, pol)
        ok, reasons = pj.check_sarcasm(toks, hits, [], 0.7, polarity=pol)
        self.assertTrue(ok)
        ok2, _ = pj.check_sarcasm(toks, hits, [], 0.7, polarity=pol, contrast=False)
        self.assertFalse(ok2)


class EventPathGuardTests(unittest.TestCase):
    """出来事との類似による疑いの、誤検出を防ぐ条件"""

    def setUp(self):
        self.pol, _ = pj.build_lexicon({"最高": 1, "おいしい": 1, "長い": -1, "疲れる": -1, "絶望": -1, "大事": 1})
        self.ev = [event("待ち時間 長い 疲れる")]

    def run_check(self, toks):
        _l, _t, hits = pj.judge(toks, self.pol)
        return pj.check_sarcasm(toks, hits, self.ev, 0.5, polarity=self.pol, contrast=False)

    def test_sarcasm_like_event_is_flagged(self):
        toks = T("待ち時間|待ち時間|名詞", "が|が|助詞", "長い|長い|形容詞", "疲れる|疲れる|動詞", "なんて|なんて|助詞", "最高|最高|名詞")
        self.assertTrue(self.run_check(toks)[0])

    def test_concessive_blocks_event_path(self):
        toks = T("待ち時間|待ち時間|名詞", "は|は|助詞", "長い|長い|形容詞", "疲れる|疲れる|動詞", "けど|けど|助詞", "、|、|記号",
                 "おいしかっ|おいしい|形容詞", "た|た|助動詞")
        self.assertFalse(self.run_check(toks)[0])

    def test_net_zero_score_blocks_event_path(self):
        toks = T("大事|大事|名詞", "な|な|助動詞", "待ち時間|待ち時間|名詞", "長い|長い|形容詞", "疲れる|疲れる|動詞", "絶望|絶望|名詞")
        self.assertFalse(self.run_check(toks)[0])


class SlangTests(unittest.TestCase):
    """辞書にない言葉(俗語・口語)の辞書と、細かく割れた語のまとめ"""

    def setUp(self):
        self.pol, _ = pj.build_lexicon()
        self.forms = pj.DEFAULT_SLANG_FORMS

    def run_tokens(self, toks):
        t = pj.wrap_tokenizer(lambda _x: toks, self.forms)("x")
        return t, pj.judge(t, self.pol)

    def test_split_adjective_is_merged(self):
        t, (label, total, _h) = self.run_tokens(T("き|き|名詞", "も|も|名詞", "かっ|かる|動詞", "た|た|助動詞"))
        self.assertEqual(t[0][1], "きもい")
        self.assertEqual(total, -1)

    def test_katakana_and_mixed_script(self):
        _t, (_l, total, _h) = self.run_tokens(T("ムカつい|ムカつく|動詞", "た|た|助動詞"))
        self.assertEqual(total, -1)
        _t, (_l, total, _h) = self.run_tokens(T("エモい|エモい|形容詞"))
        self.assertEqual(total, 1)

    def test_negation_flips_slang(self):
        _t, (_l, total, _h) = self.run_tokens(T("キモく|キモい|形容詞", "ない|ない|助動詞"))
        self.assertEqual(total, 1)

    def test_multi_token_word(self):
        t, (_l, total, _h) = self.run_tokens(T("気持ち|気持ち|名詞", "悪い|悪い|形容詞"))
        self.assertEqual(len(t), 1)
        self.assertEqual(total, -1)

    def test_unrelated_tokens_unchanged(self):
        toks = T("今日|今日|名詞", "は|は|助詞", "雨|雨|名詞")
        self.assertEqual(pj.wrap_tokenizer(lambda _x: toks, self.forms)("x"), toks)

    def test_user_words(self):
        pol, forms = pj.build_slang([("バグる", -1, "godan"), ("エグい", -1, "adj")])
        t = pj.wrap_tokenizer(lambda _x: T("バグっ|バグる|動詞", "て|て|助詞"), forms)("x")
        self.assertEqual(t[0][1], "バグる")
        self.assertEqual(pol["バグる"], -1)

    def test_suggest_words(self):
        pol, _ = pj.build_lexicon()
        lines = ["ネトゲ廃人だ", "ネトゲ廃人は最高", "今日は楽しい"]
        toks = {"ネトゲ廃人だ": T("ネトゲ廃人|ネトゲ廃人|名詞", "だ|だ|助動詞"),
                "ネトゲ廃人は最高": T("ネトゲ廃人|ネトゲ廃人|名詞", "は|は|助詞", "最高|最高|名詞"),
                "今日は楽しい": T("今日|今日|名詞", "は|は|助詞", "楽しい|楽しい|形容詞")}
        rows = pj.suggest_words(lines, lambda x: toks[x], pol, min_count=2)
        words = [r[0] for r in rows]
        self.assertIn("ネトゲ廃人", words)
        self.assertNotIn("最高", words)
        row = next(r for r in rows if r[0] == "ネトゲ廃人")
        self.assertEqual(row[1], 2)
