// Smoke test for the snippet match engine in PdfViewerModal.tsx.
// Replicates the runtime algorithm verbatim; run with `node .match-test.mjs`.
// Exit code 0 = all expected tiers reached, non-zero = regression.

const CHAR_NORM = {
  "\u2018":"'", "\u2019":"'", "\u201A":"'", "\u201B":"'",
  "\u201C":'"', "\u201D":'"', "\u201E":'"', "\u201F":'"',
  "\u2013":"-", "\u2014":"-", "\u2015":"-", "\u2010":"-", "\u2011":"-", "\u2212":"-",
  "\u00A0":" ", "\u2007":" ", "\u202F":" ", "\u2009":" ", "\u200A":" ",
  "\u200B":" ", "\u200C":" ", "\u200D":" ", "\uFEFF":" ",
};
const norm = s => Array.from(s).map(c => CHAR_NORM[c] ?? c).join("");

function flexRe(p) {
  const e = p
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\s+/g, "[\\s\\-\u2013\u2014:;,]+");
  if (!e) return null;
  try { return new RegExp(e, "i"); } catch { return null; }
}

function findBestMatch(snippet, haystack) {
  const t = snippet.trim();
  if (!t || !haystack) return null;

  const er = flexRe(t);
  if (er) {
    const m = er.exec(haystack);
    if (m) return { start: m.index, end: m.index + m[0].length, tier: "exact" };
  }

  const tokens = t.split(/\s+/).filter(Boolean);
  for (let len = Math.min(tokens.length, 30); len >= 3; len--) {
    let best = null;
    for (let s = 0; s + len <= tokens.length; s++) {
      const ph = tokens.slice(s, s + len).join(" ");
      const re = flexRe(ph);
      if (!re) continue;
      const m = re.exec(haystack);
      if (m && (!best || m[0].length > best.end - best.start)) {
        best = { start: m.index, end: m.index + m[0].length };
      }
    }
    if (best) return { ...best, tier: "phrase" };
  }

  const dist = tokens
    .map(x => x.replace(/[^A-Za-z0-9.\-]/g, ""))
    .filter(x => /^\d+(?:\.\d+)?$/.test(x) || /^[A-Za-z][A-Za-z\-]{5,}$/.test(x))
    .sort((a, b) => b.length - a.length);

  for (const tok of dist) {
    const re = new RegExp(`\\b${tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    const m = re.exec(haystack);
    if (m) return { start: m.index, end: m.index + m[0].length, tier: "token" };
  }
  return null;
}

// ── Realistic bidder PDF text ─────────────────────────────────────────────
const PDF_TEXT = `Bid Document — Acme Constructions Pvt Ltd
Annual Turnover Statement
Average Annual Turnover (FY 2021-22 to FY 2023-24): Rs. 9.23 Crore
FY 2023-24: Rs. 11.40 Crore
FY 2022-23: Rs. 9.90 Crore
FY 2021-22: Rs. 6.40 Crore
Project Experience
Total Completed Projects: 5 projects worth above Rs. 2 Crore
GSTIN: 27ABCDE1234F1Z5
ISO 9001:2015 — Certificate Valid until December 2025
Organization is not blacklisted by any Government department.`;

const HAYSTACK = norm(PDF_TEXT);

const cases = [
  { name: "verbatim turnover snippet (regex extraction)",
    snippet: "Average Annual Turnover (FY 2021-22 to FY 2023-24): Rs. 9.23 Crore",
    expectTier: "exact" },
  { name: "LLM-paraphrased turnover (phrase tier)",
    snippet: "Annual Turnover for FY 2023-24 is Rs. 11.40 Crore in their financial statement",
    expectTier: "phrase" },
  { name: "NBSP + smart quote + em-dash variant",
    snippet: "Average\u00A0Annual\u00A0Turnover \u2014 Rs.\u00A09.23\u00A0Crore",
    expectTier: "phrase" },
  { name: "synthetic 'Qualifying projects: 5' (token tier)",
    snippet: "Qualifying projects: 5",
    expectTier: "token" },
  { name: "synthetic FY values list (token tier)",
    snippet: "FY values: [11.4, 9.9, 6.4] -> avg 9.23 Crore",
    expectTier: "token" },
  { name: "GSTIN exact",
    snippet: "GSTIN: 27ABCDE1234F1Z5",
    expectTier: "exact" },
  { name: "ISO certificate (em-dash punctuation absorbed by flex regex)",
    snippet: "ISO 9001:2015 Certificate",
    expectTier: "exact" },
  { name: "blacklist sentence verbatim",
    snippet: "Organization is not blacklisted by any Government department.",
    expectTier: "exact" },
  { name: "unrelated snippet (should not match)",
    snippet: "The quick brown fox jumps over the lazy dog ABCXYZ987",
    expectTier: null },
];

let passed = 0, failed = 0;
for (const c of cases) {
  const r = findBestMatch(norm(c.snippet), HAYSTACK);
  const got = r?.tier ?? null;
  const ok = got === c.expectTier;
  const matchPreview = r ? `  match="${HAYSTACK.slice(r.start, r.end).replace(/\s+/g, " ").slice(0, 50)}"` : "";
  console.log(`${ok ? "PASS" : "FAIL"}  ${c.name.padEnd(48)} expect=${String(c.expectTier).padEnd(7)} got=${String(got).padEnd(7)}${matchPreview}`);
  if (ok) passed++; else failed++;
}
console.log("---");
console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
