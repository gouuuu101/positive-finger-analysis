# positive-judge

形態素解析(janome)と日本語評価極性辞書を使って、日本語の文がポジティブかネガティブかを判定する小さなツールです。

## 判定の流れ

1. 形態素解析で文を単語に分け、基本形(原形)に直す(「楽しかっ」→「楽しい」)
2. 感情辞書と照合して、各語に +1 / -1 を付ける
3. 同じ節にある「ない」「ません」などの否定で極性を反転する(二重否定は元に戻す)
4. 逆接(「けど」「のに」「が」)の後ろの語は2倍の重みで数える
5. 合計スコアで ポジティブ / ネガティブ / 混在 / 判定不能 を出す

## インストール

```
pip install -r requirements.txt
```

Python 3.15 などの新しい版では、fugashi(MeCab)のビルド済みパッケージがなく入らないことがあります。その場合は janome だけで動きます。
fugashi / sudachipy が入っている環境では、自動でそちらを優先して使います。

## 使い方

```
python positive_judge.py "今日はとても楽しかった!"
python positive_judge.py -v "悲しくなかった"        # 形態素の一覧も表示
python positive_judge.py -f sentences.txt            # 1行1文のテキスト(UTF-8)をまとめて判定
```

### 日本語評価極性辞書を使う

辞書本体はこのリポジトリに含めていません。実行時にURLから取得して `~/.cache/positive_judge/` に保存します(2回目以降は保存したものを使います)。

```
python positive_judge.py \
  --dict-url https://www.cl.ecei.tohoku.ac.jp/resources/sent_lex/wago.121808.pn \
  --dict-url https://www.cl.ecei.tohoku.ac.jp/resources/sent_lex/pn.csv.m3.120408.trim \
  -f sentences.txt
```

(Windows の PowerShell では、`\` ではなく1行で書いてください。)

### オプション

| オプション | 内容 |
|---|---|
| `--dict-url URL` | Webの感情辞書を取得して使う(複数可) |
| `--dict FILE` | ローカルの辞書ファイルを使う(複数可。zip / tar.gz 可) |
| `--ignore 語` | 判定から外す語(複数可。例: `--ignore サービス`) |
| `--contrast-weight N` | 逆接の後ろの重み(既定 2、`1` で無効) |
| `--min-score X` | 数値スコア付き辞書で、絶対値がX未満の語を無視(既定 0.5) |
| `--backend` | `auto` / `fugashi` / `janome` / `sudachi` / `builtin` |
| `-v` | 形態素の一覧も表示 |

## 限界

- 単語単位の判定です。皮肉や、文脈が必要な文は正しく判定できないことがあります。
- 辞書にない語は拾えません。
- スコアは極性語の個数(重み付き)の合計で、語ごとの強さは考慮しません。
- 辞書の語自体が極性を持つため、「サービス」「友達」のような語で加点されることがあります(`--ignore` で外せます)。
- 解析器が入っていない環境では、内蔵の簡易トークナイザーで動きますが、精度は大きく下がります。

## 辞書の出典と利用条件

日本語評価極性辞書(東北大学 乾・岡崎研究室)を利用します。

- 用言編: 小林ら (2005)
- 名詞編: 東山ら (2008)

配布元の公式ページに、出典として挙げる論文の詳細と利用条件の記載があります。
公式ページでは出典を明記すれば商用利用も可能とされていますが、ページには「All rights reserved」の表記もあります。公開や商用で使う前に、配布元で最新の条件を確認してください。

配布元: https://www.cl.ecei.tohoku.ac.jp/Open_Resources-Japanese_Sentiment_Polarity_Dictionary.html
