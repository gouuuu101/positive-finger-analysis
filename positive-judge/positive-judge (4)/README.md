# positive-judge

形態素解析(janome)と日本語評価極性辞書を使って、日本語の文がポジティブかネガティブかを判定する小さなツールです。

## 判定の流れ

1. 形態素解析で文を単語に分け、基本形(原形)に直す(「楽しかっ」→「楽しい」)
2. 感情辞書と照合して、各語に +1 / -1 を付ける
3. 同じ節にある「ない」「ません」などの否定で極性を反転する(二重否定は元に戻す)
4. 逆接(「けど」「のに」「が」)の後ろの語は2倍の重みで数える
5. 合計スコアで ポジティブ / ネガティブ / 混在 / 判定不能 を出す

## ダウンロードして使う(インストール不要・Windows / Mac / Linux)

このリポジトリの「Releases」から、使っているOSのファイルをダウンロードします。
形態素解析器も感情辞書も、ファイルの中に入っているので、**何もインストールせず、インターネットにつながなくても動きます**。

| OS | ファイル | 使い方 |
|---|---|---|
| Windows | `positive-judge-windows.exe` | ダブルクリックで起動 |
| Mac(Apple シリコン) | `positive-judge-macos.tar.gz` | 展開して、ターミナルから実行 |
| Linux | `positive-judge-linux.tar.gz` | 展開して、ターミナルから実行 |

起動したら、判定したい文を入力して Enter を押します。(何も入力せず Enter で終了)

**Windows**
- 「Windows によって PC が保護されました」と表示されたら、「詳細情報」→「実行」を選びます。署名のない exe では表示されることがあります。
- コマンドからも使えます: `.\positive-judge-windows.exe "今日はとても楽しかった!"`

**Mac / Linux**
```
tar -xzf positive-judge-macos.tar.gz     # Linux は positive-judge-linux.tar.gz
./positive-judge "今日はとても楽しかった!"
```
- Mac で「開発元を検証できません」と表示されたら、一度だけ次を実行してから、もう一度起動します。
  ```
  xattr -d com.apple.quarantine ./positive-judge
  ```
- Intel の Mac 用のファイルは用意していません。Intel の Mac では、下の「インストール(1行)」を使ってください。

## インストール(1行)

```
pip install git+https://github.com/<ユーザー名>/positive-judge
```

これだけで、形態素解析器(janome)も一緒に入ります。別途インストールするものはありません。

インストール後は、どちらでも実行できます。

```
positive-judge "今日はとても楽しかった!"
python -m positive_judge "今日はとても楽しかった!"
```

(`positive-judge` が見つからない場合は、`python -m positive_judge` を使ってください。)

ブラウザだけで試したい場合は、GitHub の「Code」→「Codespaces」から開くと、必要なものが入った状態で始められます。

ソースを取得して使う場合は、次のとおりです。

```
git clone https://github.com/<ユーザー名>/positive-judge
cd positive-judge
pip install -e .
```

Python 3.15 などの新しい版では、fugashi(MeCab)のビルド済みパッケージがなく入らないことがあります。janome は純Pythonなので影響を受けません。
fugashi / sudachipy が入っている環境では、自動でそちらを優先して使います。

## 使い方

```
positive-judge "今日はとても楽しかった!"
positive-judge -v "悲しくなかった"        # 形態素の一覧も表示
positive-judge -f sentences.txt            # 1行1文のテキスト(UTF-8)をまとめて判定
```

### 日本語評価極性辞書

辞書を指定しなければ、日本語評価極性辞書(東北大学 乾・岡崎研究室)を**初回に自動で取得**して使います。
辞書本体はこのリポジトリに含めていません。`~/.cache/positive_judge/` に保存し、2回目以降は保存したものを使います。
取得できないとき(オフラインなど)は、警告を出して内蔵の小さな辞書だけで判定します。

別の辞書を使う場合や、自動取得を止める場合は、次のようにします。

```
positive-judge --dict-url <辞書のURL> -f sentences.txt   # 指定した辞書だけを使う
positive-judge --dict 自作辞書.tsv "..."                   # 手元のファイルを使う
positive-judge --no-default-dict "..."                      # 内蔵の辞書だけを使う
```

### オプション

| オプション | 内容 |
|---|---|
| `--no-default-dict` | 既定の辞書の自動取得をしない(内蔵辞書だけを使う) |
| `--dict-url URL` | Webの感情辞書を取得して使う(複数可。指定すると既定の辞書は使わない) |
| `--dict FILE` | ローカルの辞書ファイルを使う(複数可。zip / tar.gz 可) |
| `--ignore 語` | 判定から外す語(複数可。例: `--ignore サービス`) |
| `--contrast-weight N` | 逆接の後ろの重み(既定 2、`1` で無効) |
| `--min-score X` | 数値スコア付き辞書で、絶対値がX未満の語を無視(既定 0.5) |
| `--backend` | `auto` / `fugashi` / `janome` / `sudachi` / `builtin` |
| `-v` | 形態素の一覧も表示 |

## 実行ファイルの作り方(管理者向け)

Windows・Mac・Linux 用のファイルは、GitHub Actions(`.github/workflows/release.yml`)が自動で作ります。
ビルドの途中で、感情辞書を配布元から取得してファイルの中に入れます。

- リリースを作る: 「Releases」→「Draft a new release」→ タグ(例: `v0.1.0`)を新規作成 →「Publish release」。
  しばらくすると、そのリリースに3つのOS用のファイルが添付されます。
- 試しにビルドだけする: 「Actions」→「Build executables」→「Run workflow」。完成したファイルは、実行結果のページの「Artifacts」からダウンロードできます。

### pip でも辞書を同梱したいとき(任意)

`pip install git+https://github.com/<ユーザー名>/positive-judge` で入れた場合、辞書は初回の実行時に自動で取得します。
辞書も一緒に入れたい場合は、次の2ファイルを `positive_judge_data/` フォルダに置いてから、コミットしてください。

- https://www.cl.ecei.tohoku.ac.jp/resources/sent_lex/wago.121808.pn
- https://www.cl.ecei.tohoku.ac.jp/resources/sent_lex/pn.csv.m3.120408.trim

2つとも置かれていれば、インターネットに接続せずに使えます。

## 限界

- 単語単位の判定です。皮肉や、文脈が必要な文は正しく判定できないことがあります。
- 辞書にない語は拾えません。
- スコアは極性語の個数(重み付き)の合計で、語ごとの強さは考慮しません。
- 辞書の語自体が極性を持つため、「サービス」「友達」のような語で加点されることがあります(`--ignore` で外せます)。
- 解析器が入っていない環境では、内蔵の簡易トークナイザーで動きますが、精度は大きく下がります。

## 辞書の出典と利用条件

日本語評価極性辞書(東北大学 乾・岡崎研究室)を利用します。実行ファイルには、この辞書が入っています。

- 用言編: 小林ら (2005)
- 名詞編: 東山ら (2008)

配布元の公式ページに、出典として挙げる論文の詳細と利用条件の記載があります。
公式ページでは出典を明記すれば商用利用も可能とされています。出典は、このリポジトリの `positive_judge_data/NOTICE.txt` と、ツールの起動時の表示に入れています。最新の条件は、配布元で確認してください。

配布元: https://www.cl.ecei.tohoku.ac.jp/Open_Resources-Japanese_Sentiment_Polarity_Dictionary.html
