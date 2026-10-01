# Keep-Alive（GitHub Action Cookie 会话保活）

基于 GitHub Actions 定时任务 + Playwright 的 **Cookie 会话保活**项目：自动访问由 [CookieLuncher](https://github.com/yhdjj131/CookiesLuncher) 导出的站点，保持各网站登录会话长期有效。

## 工作原理

1. `action_config_output.json`：CookieLuncher 导出的保活配置（**仅含 Fernet 密文**，不含明文 Cookie），每个站点一条 `site + fernet_token`
2. `COOKIE_FERNET_KEY`（GitHub Secret）：导出时打印的 Fernet 密钥，用于解密上述密文
3. `keepalive.py`：解密每个站点的 Cookie → 用 Playwright 无头浏览器打开 `https://{site}` → 检测页面是否出现「请登录」关键词，判断该站点会话是否失效 → 输出任务摘要

## 使用方法

### 1. 从 CookieLuncher 导出配置

在 CookieLuncher 中选择「主菜单 3 导出 Cookie」（或命令行 `python export_for_action.py`），得到：

- `action_config_output.json`（生成在程序根目录）
- 控制台打印的 **Fernet 密钥**（base64-urlsafe 字符串）

### 2. 更新本仓库配置文件

用新导出的 `action_config_output.json` **覆盖**本仓库根目录下的同名文件并推送：

```bash
git pull
# 用导出的文件替换 action_config_output.json
git add action_config_output.json
git commit -m "update keepalive config"
git push
```

### 3. 配置 GitHub Secret（只需一次）

仓库页面 → **Settings → Secrets and variables → Actions → New repository secret**：

| 字段 | 值 |
| --- | --- |
| Name | `COOKIE_FERNET_KEY` |
| Value | 粘贴导出时控制台打印的 Fernet 密钥 |

> 没有这个 Secret，保活任务会立即失败（脚本会报「缺少 COOKIE_FERNET_KEY」）。

### 4. 自动任务时间（已配置，无需操作）

本仓库已内置定时任务（`.github/workflows/cookie_keepalive.yml`）：

```
cron: '0 12 * * 2,4,6'（时区 Asia/Shanghai）
```

**即每周二、四、六 北京时间 12:00 自动运行一次保活任务。**

- 任务启动后，脚本会**随机延迟 0~7 分钟**再执行，避免多站点固定在整点集中访问
- 每次运行会自动安装 Python 依赖（cryptography / playwright）与 Chromium 浏览器，运行在 `ubuntu-latest`

### 5. 手动触发（可选）

仓库页面 → **Actions → Cookie会话保活 → Run workflow**，可随时手动执行一次。

### 6. 查看结果

**Actions** 页面 → 最近一次运行 → **Summary（任务摘要）**，可以看到：

- 总站点数 / 成功数 / 失败数
- 失败站点列表及原因（解密失败 / 登录已失效 / 浏览器执行异常）

如果某个站点显示「检测到登录失效关键词」，说明该站 Cookie 已过期，需要在 CookieLuncher 中重新采集/更新 Cookie 后再次导出。

## 安全说明

- 仓库中的 `action_config_output.json` **只包含 Fernet 密文**，不包含明文 Cookie；没有 `COOKIE_FERNET_KEY` Secret 无法解密，可安全提交到公开仓库
- Fernet 密钥只存于 GitHub Secret，**绝不写入仓库文件**
- **修改了 CookieLuncher 访问密码后**：必须重新导出 → 覆盖 `action_config_output.json` → 同步更新 `COOKIE_FERNET_KEY` Secret，否则密文与密钥不匹配、任务全部失败

## 项目结构

```
Keep-Alive/
├── .github/workflows/cookie_keepalive.yml  # 定时保活任务（每周二/四/六 12:00 北京时间）
├── keepalive.py                            # 保活脚本（解密 Cookie → 访问站点 → 检测失效）
├── action_config_output.json               # CookieLuncher 导出的保活配置（仅密文）
└── README.md
```
