# Zzshi3 Shadowrocket Rules

完整的 Shadowrocket 自托管规则包。56 个唯一上游规则源按照原始顺序和策略合并为 44 个远程 `.list` 文件，避免把约 17 万条规则直接展开进主配置。

## 使用

下载规则区域：

```text
https://raw.githubusercontent.com/X1-1U/Zzshi3-Shadowrocket-Rules/main/Shadowrocket-Rules.conf
```

把文件中的 `[Rule]` 区域替换到你的 Shadowrocket 主配置中。策略组名称必须与主配置一致，包括 `国外`、`国内`、`Crypto`、`其他` 等。

## 自动更新

GitHub Actions 每周日 03:17 UTC（北京时间 11:17）运行一次，即每 7 天同步全部上游、重新生成规则并校验：

- 56 个上游 URL 必须唯一且全部可以下载；
- 必须生成 44 个有序规则文件；
- 总规则量不得异常下降到 15 万条以下；
- Crypto 规则必须仍包含 Binance、OKX 和 Bybit。

如果上游没有变化，不会产生空提交。也可以在 Actions 页面手动运行 `Update Shadowrocket rules`。

## 文件

- `sources.conf`：56 个唯一上游及其策略、顺序和 `no-resolve` 设置。
- `scripts/update_rules.py`：下载、转换、合并和校验脚本。
- `rules/`：Shadowrocket 实际下载的 44 个完整规则文件。
- `Shadowrocket-Rules.conf`：可替换到主配置中的轻量 `[Rule]` 区域。

规则内容来自 `sources.conf` 中列出的各上游项目；相应内容遵循各自项目的许可与使用条款。
