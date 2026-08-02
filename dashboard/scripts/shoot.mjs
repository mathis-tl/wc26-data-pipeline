// Dev-only visual QA helper: screenshot a page at desktop+mobile widths and
// report any horizontal overflow (element wider than the viewport). Not shipped.
//   node scripts/shoot.mjs <path> <outPrefix>
import puppeteer from "puppeteer-core";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const path = process.argv[2] || "/index.html";
const prefix = process.argv[3] || "page";
const base = "http://localhost:4321";

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--hide-scrollbars"],
});

async function shoot(w, h, dsf, reduce, tag) {
  const page = await browser.newPage();
  await page.setViewport({ width: w, height: h, deviceScaleFactor: dsf });
  if (reduce) await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "reduce" }]);
  await page.goto(`${base}${path}`, { waitUntil: "networkidle0" });
  await new Promise((r) => setTimeout(r, reduce ? 200 : 1600)); // let count-up settle
  const overflow = await page.evaluate((vw) => {
    const bad = [];
    for (const el of document.querySelectorAll("*")) {
      const r = el.getBoundingClientRect();
      if (r.right > vw + 1 || r.left < -1) {
        bad.push(`${el.tagName.toLowerCase()}.${(el.className || "").toString().split(" ")[0]} right=${Math.round(r.right)}`);
      }
    }
    return {
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      offenders: [...new Set(bad)].slice(0, 8),
    };
  }, w);
  const out = `/tmp/${prefix}_${tag}.png`;
  await page.screenshot({ path: out, fullPage: true });
  const flag = overflow.scrollW > overflow.clientW ? "  ⚠ OVERFLOW" : "  ok";
  console.log(`${tag}: ${w}px  scrollW=${overflow.scrollW} clientW=${overflow.clientW}${flag}  -> ${out}`);
  if (overflow.offenders.length) console.log("   offenders:", overflow.offenders.join(" | "));
  await page.close();
}

// reduced-motion for stable full-page captures: reveals resolve to visible and
// numbers show their settled values (the below-fold observers never fire in a
// single full-page shot).
await shoot(1280, 900, 1, true, "desktop");
await shoot(390, 844, 2, true, "mobile");
await browser.close();
