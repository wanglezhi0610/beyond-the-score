import { chromium } from "playwright";

const browser = await chromium.launch({
  headless: true,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 1 });
const errors = [];
page.on("console", message => {
  if (message.type() === "error") errors.push(message.text());
});
page.on("pageerror", error => errors.push(error.message));

await page.goto("http://127.0.0.1:8765", { waitUntil: "domcontentloaded", timeout: 20000 });
await page.waitForSelector("circle.school");

const schoolCount = await page.locator("circle.school").count();
const initialChanged = await page.locator("#changed-five").textContent();
await page.locator("#weight-4").fill("40");
await page.waitForTimeout(300);
const updatedChanged = await page.locator("#changed-five").textContent();
await page.locator("#color-mode").selectOption("change");
await page.locator("#zoom-slider").fill("2.5");
await page.waitForTimeout(250);
const zoomValue = await page.locator("#zoom-slider").inputValue();
await page.locator("circle.school").first().click({ force: true });
const detailTitle = await page.locator("#detail h2").first().textContent();
const scoreDefinition = await page.locator(".score-definition").textContent();

await page.screenshot({ path: "outputs/dashboard-preview.png", fullPage: true });
console.log(JSON.stringify({ schoolCount, initialChanged, updatedChanged, zoomValue, detailTitle, scoreDefinition, errors }, null, 2));
await browser.close();
