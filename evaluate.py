"""皮肉の検出を、正解付きデータ(data/sarcasm_eval.csv)で評価する。

使い方:
    python evaluate.py                      # janome が入っていれば自動で使う
    python evaluate.py --errors             # 間違えた文も表示
    python evaluate.py --data 自分のデータ.csv

注意: data/sarcasm_eval.csv は、作者(Claude)が書いた合成データです。実際のSNSや会話の文ではないため、
数値は実データより良く出ます。「仕組みが動くか」「しきい値の目安」を見る用で、精度の保証ではありません。
CSV の列: id,text,label(皮肉/皮肉でない),category,kind,split(dev/test)
"""
import argparse
import csv
import os
import sys

import positive_judge as pj

HERE = os.path.dirname(os.path.abspath(__file__))


def load_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def prf(pairs):
    """pairs: [(正解が皮肉?, 予測が皮肉?)] → 皮肉クラスの適合率・再現率・F値・正解率"""
    tp = sum(1 for g, p in pairs if g and p)
    fp = sum(1 for g, p in pairs if not g and p)
    fn = sum(1 for g, p in pairs if g and not p)
    tn = sum(1 for g, p in pairs if not g and not p)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    acc = (tp + tn) / len(pairs) if pairs else 0.0
    return prec, rec, f1, acc, (tp, fp, fn, tn)


def main():
    pj.force_utf8_output()
    ap = argparse.ArgumentParser(description="皮肉の検出の評価")
    ap.add_argument("--data", default=os.path.join(HERE, "data", "sarcasm_eval.csv"))
    ap.add_argument("--events-corpus", default=os.path.join(HERE, "data", "events_corpus.txt"),
                    help="出来事を学習する文章(評価データとは別)")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--no-default-dict", action="store_true")
    ap.add_argument("--errors", action="store_true", help="間違えた文を表示")
    ap.add_argument("--out", help="結果を UTF-8 のファイルに保存する(PowerShell の > は文字化けするので、こちらを使う)")
    args = ap.parse_args()
    if args.out:
        sys.stdout = open(args.out, "w", encoding="utf-8-sig")

    extra = {}
    if not args.no_default_dict:
        paths = pj.bundled_dict_paths()
        try:
            if not paths:
                paths = [pj.fetch_dict(u) for u in pj.DEFAULT_DICT_URLS]
            for p in paths:
                extra.update(pj.load_dict_file(p))
        except Exception as exc:
            print(f"※ 感情辞書を取得できず、内蔵辞書だけで評価します: {exc}", file=sys.stderr)
            extra = {}
    polarity, surf = pj.build_lexicon(extra)
    name, tokenize = pj.make_backend(args.backend, surf)
    print(f"バックエンド: {name} / 外部辞書: {len(extra)} 語")
    if name.startswith("builtin"):
        print("※ 簡易トークナイザーです。出来事の照合が崩れるため、数値は参考になりません。janome を入れて実行してください。")

    lines = []
    if os.path.exists(args.events_corpus):
        with open(args.events_corpus, encoding="utf-8-sig") as fh:
            lines = [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    learned = pj.learn_events_from_lines(lines, tokenize, polarity)  # 「出来事 + 接続 + ネガティブな感情」の形の文だけから取り出す
    events = pj.build_events(tokenize, True, (), learned)
    print(f"ネガティブな出来事: {len(events)} 件(見本 + 学習用文章 {len(lines)} 行から {len(learned)} 件を抽出)\n")

    rows = load_rows(args.data)
    eval_texts = {r["text"].strip() for r in rows}
    overlap = [l for l in lines if l in eval_texts]
    if overlap:
        print(f"※ 警告: 学習用文章のうち {len(overlap)} 行が、評価データと同じ文です。数値が実際より良く出ます。")
    cache = {}

    def tok(text):
        if text not in cache:
            cache[text] = tokenize(text)
        return cache[text]

    def predict(row, th, contrast=True):
        r = pj.analyze(row["text"], tok, polarity, 2,
                       {"mode": "flag", "events": events, "threshold": th, "contrast": contrast})
        return r

    # 1) 何もしないとき(辞書だけ): 皮肉の文が「ポジティブ」と判定される割合
    sar = [r for r in rows if r["label"] == "皮肉"]
    plain = [pj.analyze(r["text"], tok, polarity, 2, None) for r in sar]
    n_pos = sum(1 for a in plain if a["label"] == "ポジティブ")
    print(f"[辞書だけ] 皮肉 {len(sar)} 件のうち、ポジティブと誤判定: {n_pos} 件 ({n_pos / len(sar):.0%})")
    flagged = sum(1 for r in sar if predict(r, 0.7)["sarcasm"])
    print(f"[今の仕組み(しきい値0.7)] 皮肉 {len(sar)} 件のうち、「皮肉の可能性あり」にできた: {flagged} 件\n")

    # 2) しきい値を dev で選び、test で評価する
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    sweep = [round(0.3 + 0.1 * i, 1) for i in range(8)]
    best_th, best_f = 0.7, -1.0
    print("しきい値ごとの F値(dev):")
    for th in sweep:
        f = prf([(r["label"] == "皮肉", predict(r, th)["sarcasm"]) for r in dev])[2]
        print(f"  {th:.1f}: {f:.3f}")
        if f > best_f:
            best_th, best_f = th, f
    print(f"→ dev で最良のしきい値: {best_th}\n")

    def show(title, subset, th):
        pairs = [(r["label"] == "皮肉", predict(r, th)["sarcasm"]) for r in subset]
        p, rc, f, acc, (tp, fp, fn, tn) = prf(pairs)
        print(f"[{title}] しきい値 {th}: 適合率 {p:.3f} / 再現率 {rc:.3f} / F値 {f:.3f} / 正解率 {acc:.3f}  (TP{tp} FP{fp} FN{fn} TN{tn})")

    show("test", test, 0.7)
    if best_th != 0.7:
        show("test", test, best_th)

    # 2.5) 方式の比較: 出来事の照合だけ / 対比ルールだけ / 両方
    print("\n方式の比較(適合率 / 再現率 / F値):")
    configs = [("出来事の照合だけ(0.7)", 0.7, False), (f"出来事の照合だけ({best_th})", best_th, False),
               ("対比ルールだけ", 9.0, True), ("両方(0.7)", 0.7, True), (f"両方({best_th})", best_th, True)]
    for title, th, ct in configs:
        for part_name, part in (("全体", rows), ("test", test)):
            pr, rc, f, acc, _ = prf([(r["label"] == "皮肉", predict(r, th, ct)["sarcasm"]) for r in part])
            print(f"  {title:<22} {part_name:<3}: {pr:.3f} / {rc:.3f} / {f:.3f}")

    # 3) カテゴリ別(test, 既定のしきい値)
    print("\nカテゴリ別(全データ, しきい値 0.7)の再現率・誤検出:")
    for cat in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == cat]
        s = [r for r in sub if r["label"] == "皮肉"]
        n = [r for r in sub if r["label"] != "皮肉"]
        hit = sum(1 for r in s if predict(r, 0.7)["sarcasm"])
        fp = sum(1 for r in n if predict(r, 0.7)["sarcasm"])
        print(f"  {cat}: 皮肉 {hit}/{len(s)} を検出 / 皮肉でない {fp}/{len(n)} を誤検出")

    if args.errors:
        print("\n間違い(しきい値 0.7):")
        for r in rows:
            gold, pred = r["label"] == "皮肉", predict(r, 0.7)["sarcasm"]
            if gold != pred:
                print(f"  {'見逃し' if gold else '誤検出'} [{r['kind']}] {r['text']}")


if __name__ == "__main__":
    main()
    if sys.stdout is not sys.__stdout__:
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        print("結果を保存しました。")
