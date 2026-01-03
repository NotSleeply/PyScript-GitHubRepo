# GitHub 仓库自动下载工具

这是一个用于自动下载指定 GitHub 用户仓库代码的工具，通过 Selenium 模拟浏览器操作，实现批量下载仓库的 ZIP 压缩包。

## 功能说明

- 自动获取目标 GitHub 用户的仓库总数

- 分页遍历用户的所有仓库

- 自动点击进入仓库、打开下载菜单并下载 ZIP 包

- 支持 Chrome 和 Edge 两种浏览器

## 环境依赖

- Python 3.x

- 所需 Python 库：

- requests

- [`beautifulsoup4`](https://beautifulsoup.cn) : 爬虫
  - [林粒粒讲Python](https://www.bilibili.com/video/BV1EHdUYEEEj)

- [`selenium`](https://www.selenium.dev/zh-cn/): 
  - [2025最新Selenium教程(Python 网页自动化测试脚本)](https://www.bilibili.com/video/BV1Y9UPYAEqN) : 相关教程;

## 安装步骤

1. 安装依赖库：

``` powershell
pip install -r requirements.txt
```

1. 下载对应浏览器的驱动：

- Chrome 驱动：[chro](https://sites.google.com/chromium.org/driver/)[medri](https://sites.google.com/chromium.org/driver/)[ver](https://sites.google.com/chromium.org/driver/)

- Edge 驱动：[msed](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)[gedri](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)[ver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)

- 将下载的驱动放在项目根目录的 drivers 文件夹下

## 使用方法

1. 修改 url 为目标 GitHub 用户的仓库页面地址

1. 选择要使用的浏览器（Chrome 或 Edge）

1. 运行主程序：

``` shell
make run
```

## 注意事项

- 下载速度取决于网络状况和仓库大小，请根据实际情况调整 waitDownTime

- 程序会自动处理分页，无需手动干预

- 若遇到元素定位失败的问题，可能是 GitHub 页面结构更新导致，需相应调整 XPath 表达式

## 免责声明

本工具仅用于学习和研究目的，使用者应自行承担使用本工具的一切风险和责任。请遵守以下原则：

- 遵守 GitHub 的使用条款和访问速率限制
- 尊重开源项目作者的知识产权和许可协议
- 不要将下载的代码用于商业用途（除非原项目许可证明确允许）
- 本工具的开发者不对因使用本工具而可能导致的任何问题或损失负责

使用本工具即表示您同意上述免责声明。如果您不同意，请勿使用本工具。
