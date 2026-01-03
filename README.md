# GitHub 仓库自动下载工具

这是一个用于自动下载指定 GitHub 用户仓库代码的工具，通过 Selenium 模拟浏览器操作，实现批量下载仓库的 ZIP 压缩包。

## 功能说明

- 自动获取目标 GitHub 用户的仓库总数

- 分页遍历用户的所有仓库

- 自动点击进入仓库、打开下载菜单并下载 ZIP 包

- 支持 Chrome 和 Edge 两种浏览器

- [`selenium`](https://www.selenium.dev/zh-cn/):
  - [2025最新Selenium教程(Python 网页自动化测试脚本)](https://www.bilibili.com/video/BV1Y9UPYAEqN) : 相关教程;

## 安装步骤

1. 安装依赖库：

``` powershell
pip install -r requirements.txt
```

1. 下载对应浏览器的驱动：

- Chrome 驱动：[chromedriver](https://googlechromelabs.github.io/chrome-for-testing/)

- Edge 驱动：[msedgedriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/?form=MA13LH#downloads)

## 免责声明

本工具仅用于学习和研究目的，使用者应自行承担使用本工具的一切风险和责任。请遵守以下原则：

- 遵守 GitHub 的使用条款和访问速率限制
- 尊重开源项目作者的知识产权和许可协议
- 不要将下载的代码用于商业用途（除非原项目许可证明确允许）
- 本工具的开发者不对因使用本工具而可能导致的任何问题或损失负责

使用本工具即表示您同意上述免责声明。如果您不同意，请勿使用本工具。
