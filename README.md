# BJFU PhD Notice Monitor

监控北京林业大学研究生院博士招生通知页：
- 页面：<https://graduate.bjfu.edu.cn/zsgl/bszs/index.html>
- 运行方式：GitHub Actions
- 频率：每 12 小时一次
- 通知方式：163 SMTP 邮件

## 功能

- 抓取博士招生通知列表
- 提取标题、日期、链接
- 与 `state.json` 对比，发现新增通知
- 有新增时发送邮件
- 每次运行后自动提交最新 `state.json` 回仓库，作为下次比对基线

## 需要配置的 GitHub Secrets

进入仓库：`Settings -> Secrets and variables -> Actions`，添加：

- `SMTP_HOST`：`smtp.163.com`
- `SMTP_PORT`：`465`
- `SMTP_USER`：你的 163 发件邮箱，例如 `xxx@163.com`
- `SMTP_PASS`：163 邮箱 SMTP 授权码（不是登录密码）
- `EMAIL_TO`：`liyalun56@163.com`

## 工作流

- 自动执行：每 12 小时
- 手动执行：Actions 页面中 `Run workflow`

## 说明

- 首次运行只会初始化 `state.json`，不会发送邮件，避免历史通知被全部视为“新增”。
- 如果学校页面结构改了，脚本可能需要调整解析规则。
- 若你想更快收到通知，可以把定时改成每 1 小时一次。
