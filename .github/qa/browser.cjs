const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const BASE = "http://127.0.0.1:4173/uni-lecture-tutor-website/";
const ARTIFACTS = process.env.QA_ARTIFACTS || "qa-artifacts";
const langs = ["en", "de", "ar"];
const pages = ["", "getting-started.html", "learning-science.html", "privacy.html", "terms.html", "support.html", "legal.html"];
const profiles = [
  {name: "desktop-light", viewport: {width: 1440, height: 900}, colorScheme: "light"},
  {name: "mobile-dark", viewport: {width: 390, height: 844}, colorScheme: "dark"},
  {name: "small-mobile-light", viewport: {width: 320, height: 720}, colorScheme: "light", homeOnly: true},
  {name: "tablet-dark", viewport: {width: 768, height: 1024}, colorScheme: "dark", homeOnly: true}
];
const prefix = lang => lang === "en" ? "" : lang + "/";
(async () => {
  fs.mkdirSync(ARTIFACTS, {recursive: true});
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_EXECUTABLE ? {executablePath: process.env.CHROMIUM_EXECUTABLE} : {})});
  const failures = [];
  let checked = 0;
  try {
    for (const profile of profiles) {
      const context = await browser.newContext({viewport: profile.viewport, colorScheme: profile.colorScheme, reducedMotion: "reduce", permissions: ["clipboard-read", "clipboard-write"]});
      const page = await context.newPage();
      const runtime = [];
      page.on("pageerror", e => runtime.push("JavaScript error: " + e.message));
      page.on("requestfailed", r => runtime.push("Request failed: " + r.url()));
      page.on("request", r => {
        if (!r.url().startsWith(BASE) && !r.url().startsWith("data:") && !r.url().startsWith("blob:")) runtime.push("Unexpected external request: " + r.url());
      });
      page.on("response", r => {
        if (r.status() >= 400) runtime.push("HTTP " + r.status() + ": " + r.url());
      });
      for (const lang of langs) {
        for (const item of profile.homeOnly ? [""] : pages) {
          const label = profile.name + "/" + lang + "/" + (item || "home");
          try {
            runtime.length = 0;
            const response = await page.goto(BASE + prefix(lang) + item, {waitUntil: "load"});
            assert.equal(response.status(), 200);
            assert.equal(await page.locator("html").getAttribute("lang"), lang);
            assert.equal(await page.locator("html").getAttribute("dir"), lang === "ar" ? "rtl" : "ltr");
            assert.equal(await page.locator("h1").count(), 1);
            const size = await page.evaluate(() => ({width: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth}));
            assert.ok(size.width <= size.viewport + 1, "horizontal overflow: " + JSON.stringify(size));
            assert.equal(await page.locator("[data-theme-toggle]").getAttribute("aria-pressed"), String(profile.colorScheme === "dark"));
            await page.addScriptTag({path: require.resolve("axe-core/axe.min.js")});
            const violations = await page.evaluate(async () => (await axe.run(document, {runOnly: {type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}})).violations.map(v => ({id: v.id, impact: v.impact, targets: v.nodes.map(n => n.target)})));
            assert.equal(violations.length, 0, "axe: " + JSON.stringify(violations));
            if (item === "") {
              assert.equal(await page.locator(".discipline-icon").count(), 24);
              assert.equal(await page.locator(".demo-extras li").count(), 4);
              const theme = page.locator("[data-theme-toggle]");
              await theme.click();
              assert.equal(await theme.getAttribute("aria-pressed"), String(profile.colorScheme !== "dark"));
              await theme.click();
              if (profile.viewport.width <= 928) {
                const menu = page.locator("[data-menu-toggle]");
                await menu.click();
                assert.equal(await menu.getAttribute("aria-expanded"), "true");
                await page.keyboard.press("Escape");
                assert.equal(await menu.getAttribute("aria-expanded"), "false");
                assert.ok(await menu.evaluate(el => el === document.activeElement));
              }
              await page.locator("#tab-plan").click();
              assert.equal(await page.locator("#tab-plan").getAttribute("aria-selected"), "true");
              await page.keyboard.press(profile.viewport.width <= 544 ? (lang === "ar" ? "ArrowLeft" : "ArrowRight") : "ArrowDown");
              assert.equal(await page.locator("#tab-learn").getAttribute("aria-selected"), "true");
              await page.locator("[data-sample-next]").click();
              assert.equal(await page.locator("#tab-practice").getAttribute("aria-selected"), "true");
              for (const [value, attr] of [["2", "data-retry"], ["4", "data-correct"]]) {
                await page.locator("input[value='" + value + "']").check();
                await page.locator("[data-quiz] button[type='submit']").click();
                assert.equal(await page.locator(".quiz-feedback").textContent(), await page.locator("[data-quiz]").getAttribute(attr));
              }
              await page.locator("#tab-learn").click();
              await page.evaluate(() => window.scrollTo(0, 0));
              await page.screenshot({path: path.join(ARTIFACTS, lang + "-" + profile.name + ".png"), fullPage: true, animations: "disabled"});
            } else if (item === "getting-started.html") {
              assert.equal(await page.locator(".guide-steps > li").count(), 5);
              assert.equal(await page.locator(".prompt-list blockquote").count(), 3);
              if (await page.locator(".copy-prompt").count()) {
                await page.locator(".copy-prompt").first().click();
                const expected = (await page.locator(".prompt-list blockquote > p").first().textContent()).trim();
                assert.equal(await page.evaluate(() => navigator.clipboard.readText()), expected);
              }
            } else if (item === "learning-science.html") {
              assert.equal(await page.locator(".upgrade-science .upgrade-card").count(), 11);
            }
            assert.deepEqual(runtime, []);
            checked++;
          } catch (e) {
            failures.push(label + ": " + e.message);
          }
        }
      }
      await context.close();
    }
    const noJS = await browser.newContext({javaScriptEnabled: false});
    const p = await noJS.newPage();
    for (const lang of langs) {
      await p.goto(BASE + prefix(lang));
      assert.ok(await p.locator("[data-quiz-fallback]").isVisible(), lang + ": no-JS quiz fallback");
      assert.ok(await p.locator("#demo-plan").isVisible(), lang + ": no-JS lesson fallback");
      assert.ok(await p.locator(".languages").isVisible(), lang + ": no-JS navigation");
    }
    const missing = await p.goto(BASE + "nested/does-not-exist");
    assert.equal(missing.status(), 404);
    assert.equal(await p.locator("h1").textContent(), "Page not found");
    await noJS.close();
  } finally { await browser.close(); }
  console.log(JSON.stringify({checked, failures}, null, 2));
  if (failures.length) process.exitCode = 1;
})().catch(err => { console.error(err); process.exitCode = 1; });
