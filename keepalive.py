import json
import os
from cryptography.fernet import Fernet, InvalidToken
from playwright.sync_api import sync_playwright

SUMMARY_PATH = os.environ.get("GITHUB_STEP_SUMMARY", "/tmp/summary.md")
CONFIG_FILENAME = "action_config_output.json"


def write_summary(content: str):
    with open(SUMMARY_PATH, "a", encoding="utf-8") as f:
        f.write(content + "\n")


def main():
    fernet_key_b64 = os.environ.get("COOKIE_FERNET_KEY")

    if not fernet_key_b64:
        print("错误：缺少 COOKIE_FERNET_KEY")
        write_summary("# 任务失败\n- 缺少 Secret：COOKIE_FERNET_KEY")
        exit(1)

    if not os.path.exists(CONFIG_FILENAME):
        print(f"错误：缺少 {CONFIG_FILENAME}")
        write_summary(f"# 任务失败\n- 缺少配置文件：{CONFIG_FILENAME}")
        exit(1)

    with open(CONFIG_FILENAME, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    global_cfg = cfg.get("global", {})
    cookie_items = cfg.get("cookies", [])

    fernet = Fernet(fernet_key_b64)
    results = []
    global_decrypt_failed = False

    for item in cookie_items:
        site = item.get("site", "")
        token = item.get("fernet_token", "")

        res = {"site": site or "未知站点", "ok": False, "msg": ""}

        if not site or not token:
            res["msg"] = "site 或 fernet_token 为空"
            results.append(res)
            print(f"跳过：{res['msg']}")
            continue

        visit_url = f"https://{site}"

        try:
            raw_bytes = fernet.decrypt(token.encode("utf-8"))
            cookie_array = json.loads(raw_bytes.decode("utf-8"))
        except InvalidToken:
            res["msg"] = "密文解密失败，可能密钥错误或密文被篡改"
            results.append(res)

            if len(results) == 1:
                global_decrypt_failed = True

            print(f"解密失败：{site}")
            continue
        except Exception as e:
            res["msg"] = f"解密异常：{str(e)}"
            results.append(res)
            print(f"解密异常：{site}")
            continue

        try:
            timeout = int(global_cfg.get("timeout", 30000))
            login_invalid_keyword = global_cfg.get("loginInvalidKeyword", "请登录")
            user_agent = global_cfg.get(
                "userAgent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                ctx = browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1280, "height": 720}
                )
                ctx.add_cookies(cookie_array)
                page = ctx.new_page()
                page.goto(visit_url, wait_until="networkidle", timeout=timeout)
                page_text = page.content()

                if login_invalid_keyword in page_text:
                    res["msg"] = "检测到登录失效关键词，Cookie 可能已失效"
                    browser.close()
                    results.append(res)
                    print(f"保活失败：{site}")
                    continue

                res["ok"] = True
                res["msg"] = "会话保活成功"
                browser.close()
                print(f"保活成功：{site}")

        except Exception as e:
            res["msg"] = f"浏览器执行异常：{str(e)}"
            print(f"执行异常：{site}")

        results.append(res)

    success_list = [r for r in results if r["ok"]]
    fail_list = [r for r in results if not r["ok"]]

    write_summary("## Cookie 会话保活任务汇总\n")
    write_summary(f"- 总站点数：{len(results)}")
    write_summary(f"- 成功：{len(success_list)}")
    write_summary(f"- 失败：{len(fail_list)}")

    if fail_list:
        write_summary("\n### 失败站点\n")
        for f in fail_list:
            write_summary(f"- **{f['site']}**：{f['msg']}")

    if global_decrypt_failed:
        print("全局密钥错误，任务终止")
        exit(1)


if __name__ == "__main__":
    main()
