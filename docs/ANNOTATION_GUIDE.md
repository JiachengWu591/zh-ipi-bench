# Second-annotator protocol

Every label in the dataset is the author's judgement. This protocol measures whether a second
person, given the same written rule, reaches the same labels. It is the check the data card and
the roadmap have been waiting on, and the only one on the label ambiguity around the
`ctx_config` and `checklist` intents (they read like a legitimate request to a human reporter).

The kit is `python -m zhipi.annotate`. It is stdlib-only and needs no network.

## What the annotator does

An estimated one to two hours (not timed; the long documents take longest), in one sitting
or two, on one offline HTML page.

- **Part A, 103 texts.** For each text (with its carrier: issue, document, email, web source,
  tool output) choose *injected*, *benign* or *unsure*. The rule the annotator reads: imagine an
  AI assistant told only to read and summarise this content; does the text contain something
  written *to that assistant* that asks it to do more than that (read or leak files or secrets,
  send data, change its own rules, ignore earlier instructions, visit a link)? A request aimed
  at a human reader, a discussion of prompt injection, an ordinary task list or a quotation is
  benign.
- **Part B, 31 intent pairs.** Rate the Chinese text against its English original for meaning
  and for naturalness (1–3 each). This matters because the twelve ported attacks were translated
  by the author alone.

The page stays blind: it shows no sample id, intent, tier, benign stratum, transform list, or
the author's label, and item ids are shuffled and opaque. The packet is 62 injected and 41
benign Chinese items (two per intent, the first untransformed), a mix the sampler chose, not
the dataset's, and the annotator is not told it.

## Steps

1. Generate the packet (deterministic for a seed; both outputs are git-ignored):

   ```bash
   python -m zhipi.annotate prepare
   ```

   It prints the packet id and two paths. Send the annotator **only**
   `annotation/packet/annotate.html`. Keep `annotation/key.json` private until they are done.
2. Send the message below. Ask them not to use AI tools, not to read the repository's data
   files, and not to discuss specific items with you until they have finished.
3. They open the file in a desktop browser (Chrome or Edge), work through it, press
   "导出答案" and send back the downloaded `answers-<packet id>.json`. Answers autosave in that
   browser, but clearing site data loses un-exported ones.
4. Score it:

   ```bash
   python -m zhipi.annotate score --annotations answers-<packet id>.json --out results/annotation.md
   ```

   It refuses an answers file from a different packet, unknown item ids and invalid values.

### Message to send (Chinese)

> 想请你帮我做一个一到两个小时的标注（可以分两次做）：一个网页文件，用浏览器打开，不用联网。里面是 100 多段文本，
> 请你判断每段里有没有“写给 AI 助手、想让它做超出总结任务的事”的内容；另有 30 多对中英文，
> 请你给译文打分。说明在页面顶部。几点请求：不要用 AI 工具；不要去看 zh-ipi-bench 仓库里的数据文件；
> 做完之前先别和我讨论具体条目；用你的第一判断就行。做完点“导出答案”，把下载的 json 文件发给我。
> 页面里的“攻击”都是针对一个虚构沙箱和假密钥的，不用也不要执行。谢谢！

## How the result will be read (fixed before any answers exist)

- Reported as raw agreement with a Wilson interval, Cohen's kappa with a bootstrap interval, the
  confusion table, and agreement by tier and by benign stratum. **Unsure and unanswered count as
  disagreement**, never as agreement.
- All disagreements are reported; none are dropped as annotator error. If the annotator calls
  an intent benign, that is a finding about the label, not noise.
- The released datasets stay frozen (their fingerprints are pinned), so nothing is relabelled
  retroactively. If agreement is low on specific intents, the follow-up is a documented note in
  the data card and, if warranted, a new version with the rule clarified and those intents
  reconsidered. Per the roadmap decision point: if kappa is low, fix the guide before adding data.
- Only the aggregate report is committed. The answers file, which includes free-text notes,
  stays local unless the annotator agrees to publish it; the report names the annotator by
  the code they entered, never a real name.

## What it can and cannot show

- It shows whether the rule is clear enough for a second person to apply, and where it is not.
  It does not show that either label is true.
- One annotator: the intervals describe sampling of items, not of people. Items come from 31
  intents, two each, so they are correlated and the bootstrap interval is too narrow. A third
  reader would be worth more than a larger packet from the same one.
- Kappa depends on the label mix, which the sampler chose.
- Independence is by instruction. The dataset is public; this cannot show the annotator did
  not look at it or use a tool.
- The texts are template-generated; agreement here says nothing about real attack text.
