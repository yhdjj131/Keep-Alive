const { chromium } = require('playwright');

// ====================== 【可配置项，自行修改】======================
const CONFIG = {
  TARGET_URL: "https://xxx.com",        // 保活主页地址
  SIGN_URL: "https://xxx.com/sign",      // 签到接口/页面地址
  LOGIN_INVALID_KEYWORD: "请登录",       // 页面出现该文字代表Cookie失效
  TIMEOUT: 30000,
  USER_AGENT: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  // 启用的账号列表，和环境变量一一对应
  ACCOUNT_LIST: [
    { id: 1, envKey: "COOKIE_B64_1" },
    { id: 2, envKey: "COOKIE_B64_2" },
    { id: 3, envKey: "COOKIE_B64_3" }
  ]
};
// =================================================================

async function singleAccountTask(account) {
  const cookieB64 = process.env[account.envKey];
  if (!cookieB64) {
    return { ok: false, msg: `环境变量 ${account.envKey} 不存在` };
  }

  // Base64解码Cookie
  const cookieRaw = Buffer.from(cookieB64, "base64").toString();
  const cookies = JSON.parse(cookieRaw);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    cookies: cookies,
    userAgent: CONFIG.USER_AGENT
  });
  const page = await ctx.newPage();

  try {
    // 1.访问主页保活会话
    await page.goto(CONFIG.TARGET_URL, {
      waitUntil: "networkidle",
      timeout: CONFIG.TIMEOUT
    });

    const pageText = await page.content();
    if (pageText.includes(CONFIG.LOGIN_INVALID_KEYWORD)) {
      return { ok: false, msg: "Cookie失效，检测到登录页" };
    }
    console.log(`【账号${account.id}】主页访问成功，会话保活完成`);

    // 2.执行签到逻辑
    await page.goto(CONFIG.SIGN_URL, {
      waitUntil: "networkidle",
      timeout: CONFIG.TIMEOUT
    });
    console.log(`【账号${account.id}】签到页面访问完成`);

    return { ok: true, msg: "保活+签到成功" };
  } catch (err) {
    return { ok: false, msg: err.message };
  } finally {
    await browser.close();
  }
}

async function main() {
  const resultList = [];
  for (const acc of CONFIG.ACCOUNT_LIST) {
    console.log(`===== 开始执行账号 ${acc.id} =====`);
    const res = await singleAccountTask(acc);
    resultList.push({ accountId: acc.id, ...res });
    console.log(`【账号${acc.id}】结果: ${res.ok ? "✅成功" : "❌失败"}，信息：${res.msg}\n`);
  }

  // 汇总报表
  const successCnt = resultList.filter(x => x.ok).length;
  const failList = resultList.filter(x => !x.ok).map(x => x.accountId);
  console.log("===== 任务汇总 =====");
  console.log(`总账号:${resultList.length}，成功:${successCnt}，失败账号:${failList.join(",") || "无"}`);

  // 只要存在失败账号，job标记失败
  if (failList.length > 0) {
    process.exit(1);
  }
}

main().catch(e => {
  console.error("全局异常：", e.message);
  process.exit(1);
});
