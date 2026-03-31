# GitHub 仓库自动同步下载工具 (PyScript-GitHubRepo)

一个现代化、高效、强健的 Python 工具，用于通过 GitHub API 批量下载或同步指定用户的所有开源仓库。完全摒弃了缓慢且容易出错的浏览器自动化（Selenium）方案，现已全面重构并模块化，为您提供丝滑的克隆与备份体验。

## ✨ 核心特性

- **🚀 多线程极速并发**：原生内置多线程支持（通过 `max_workers` 配置），海量仓库极速克隆或下载，不再需要等待单个排队。
- **📦 双模式支持：Git Clone 与 ZIP 解压**
  - **Git 模式**：通过 `GitPython`，本地若已有此仓库则自动触发 `git pull` 更新，否则 `git clone`，完美保留历史 Commit 和 Git 记录。
  - **ZIP 模式**：使用 API 极速拉取打包的 Zip 源码文件并**自动解压处理**，自动清理带分支后缀（如 `repo-main`）的无用目录文件夹，还您清爽整洁的项目名。
- **🔍 强大的按条件筛选**：
  - `language`：仅下载指定编程语言的项目（如 `Python`, `JavaScript`）
  - `min_stars`：设置最小星标数阈值，过滤掉无用仓库
  - `updated_after`：指定日期后有更新的活跃仓库才被下载
  - `max_repos`：限制最大操作仓库数，节省流量
- **🔀 智能分支回退（Fallback）**：设定任意你想拉取的指定分支 `target_ref`。若该目标分支（或 Tag）不存在，系统将自动询问其真实**默认分支**并无感下潜回退，大幅消除 404/Branch Not Found 报错！
- **♻️ 增量同步断点策略**：在目标目录通过 `last_sync.json` 文件全自动记录更新时间戳。如果没有新变更，工具直接跳过不浪费任何资源。
- **🛡 重试与容错机制**：基于 `Tenacity` 的指数重试逻辑。自动辨别并处理网络波动波动、502 错误，把严重致命错误打印至日志 `app.log`，不再由于一个仓库坏掉导致整个进度崩溃。
- **📊 自动化清单报表**：在下载结束时根据结果于目标目录（默认 `./reports`）生成 Markdown 或 CSV 格式的汇总报告。
- **🎨 极美的命令行交互界面**：基于 `Rich` 构建的动态排版进度条，多任务执行状况一针见血，摆脱日志刷屏烦恼。

## 🚀 快速启动

### 1. 同步环境并安装依赖

利用 `uv` 极速搭建虚拟环境及并配置项目所需库（GitPython, PyYAML, rich, tenacity 等）：

```powershell
uv sync
```

### 2. 准备配置 (极其重要！)

在克隆或拉取大规模数量的内容时，极其容易触发 Github 的无授权访问速率限制 (Rate limit)。我们需要先提供一枚 Token：

1. 访问你的 GitHub 账号生成 Token 页面：[Generate new token (classic)](https://github.com/settings/tokens)
2. 无需勾选复杂权限（若只需下载公开仓库），生成并复制你的以 `ghp_` 开头的 Token。
3. 复制项目根目录下的配置参考文件：

```powershell
cp config.example.yaml config.yaml
```

修改 `config.yaml` 填入你的信息：

```yaml
github:
  username: "codewithsadee" # 想要爬取下载的 Github 用户名
  token: "ghp_XXXXXXXXXXXXXXXXXXXXXXXXXXX"  # 填入你的 Token 防止被限流

download:
  mode: "git"            # "zip" 或 "git"
  save_path: "./repos"   # 仓库存放的目录
  target_ref: "main"     # 默认拉取的分支或 Tag
```

### 3. 开始执行

直接通过入口文件一键运行：

```powershell
uv run main.py
```

当然，你可以使用 **CLI 命令行参数** 对任意 YAML 配置进行临时覆盖重写：

```powershell
# 只下载最新的 3 个 Python 相关的带星仓库：
uv run main.py --username tiangolo --language Python --min-stars 50 --max-repos 3 --mode git
```

执行完毕后系统将输出优美的总结报表，你也可以去目录内查看自动生成的 `.md` 文档报告哦！

## 免责声明

本工具仅用于学习和研究目的，使用者应自行承担使用本工具的一切风险和责任。请遵守以下原则：

- 遵守 GitHub 的使用条款和访问速率限制
- 尊重开源项目作者的知识产权和许可协议
- 不要将下载的代码用于商业用途（除非原项目许可证明确允许）
- 本工具的开发者不对因使用本工具而可能导致的任何问题或损失负责

使用本工具即表示您同意上述免责声明。如果您不同意，请勿使用本工具。
