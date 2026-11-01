#!/usr/bin/env node
// Fill ONE form field in the operator's Chromium with a secret from the macOS Keychain,
// without the value ever reaching Claude: the agent passes a HANDLE, this process fetches the
// value with `secret exec`, writes it over CDP, and prints only the length.
//
//   node .claude/tools/fill-secret.mjs --handle travel:passport:number \
//        --host www.airline.example --label "Passport number"      (or --selector 'input[name=x]')
//   node .claude/tools/fill-secret.mjs --handle travel:passport:expiry --format DD ...
//   node .claude/tools/fill-secret.mjs --handle travel:passport:expiry --verify-date
//        (prints ok/refused only — checks the stored layout without showing the value)
//
// --format splits or re-lays a date stored as YYYY-MM-DD, so ONE stored expiry serves split
// day/month/year boxes and other layouts (no second copy to drift). Tokens: YYYY YY MMMM MMM MM
// M DD D (every D, M or Y is a token); other characters are copied ("DD/MM/YYYY", "MM/YY"). A <select> is matched by
// option value, then by option text, case-insensitively (so MMM fits a "May" dropdown).
//
// Refuses unless (1) hostpolicy.py allows this handle on this host (the one allowlist, read
// from ${AGENTIC_NOMAD_HOSTS:-~/.config/agentic-nomad/hosts.json}; missing → refused),
// (2) exactly one open tab is on that host, (3) the page itself still reports that
// host, and (4) exactly one visible field matches. Records {host, label, length} in
// .claude/state/fills.json so page_scope.py redacts that field from later snapshots.
// Runtime: Node 22's built-in WebSocket and fetch (nodejs_22 is pinned in flake.nix) — no deps.
// Rejected: a Python filler (stdlib has no WebSocket client; hand-rolling one is the wheel),
// typing via the MCP `fill` tool (the value would be in the tool call, i.e. the transcript).

import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const HOOKS = join(HERE, "..", "hooks");
const STATE = join(HERE, "..", "state");
const CDP = process.env.NOMAD_CDP_URL || "http://127.0.0.1:9222";

function die(msg, code = 1) {
  console.error(`fill-secret: refused: ${msg}`);
  process.exit(code);
}

function args(argv) {
  if (argv.length === 3 && argv[0] === "--handle" && argv[2] === "--verify-date")
    return { handle: argv[1], verifyDate: true };
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    const k = argv[i];
    if (!["--handle", "--host", "--label", "--selector", "--format"].includes(k) || argv[i + 1] === undefined)
      die(`bad argument ${k}`, 2);
    out[k.slice(2)] = argv[i + 1];
  }
  if (!out.handle || !out.host || !(out.label || out.selector) || (out.label && out.selector))
    die("need --handle, --host and exactly one of --label / --selector", 2);
  return out;
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];

// Never put the value in an error: callers print errors.
export function formatDate(value, format) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) throw new Error("stored value is not YYYY-MM-DD, so --format cannot apply");
  const [, y, mo, d] = m;
  const mi = Number(mo) - 1;
  if (mi < 0 || mi > 11 || Number(d) < 1 || Number(d) > 31) throw new Error("stored date is out of range");
  const tok = { YYYY: y, YY: y.slice(2), MMMM: MONTHS[mi], MMM: MONTHS[mi].slice(0, 3), MM: mo,
    M: String(Number(mo)), DD: d, D: String(Number(d)) };
  return format.replace(/YYYY|YY|MMMM|MMM|MM|M|DD|D/g, (t) => tok[t]);
}

export function hostMatches(host, allowed) {
  host = (host || "").toLowerCase().replace(/\.$/, "");
  allowed = allowed.toLowerCase();
  return host !== "" && (host === allowed || host.endsWith("." + allowed));
}

// Runs IN THE PAGE. Finds exactly one visible field, sets it the way a user would (native
// setter + input/change events, so React/Angular forms see it), and masks it for screenshots.
function pageFill(want, label, selector, value) {
  const host = location.hostname.toLowerCase();
  if (!(host === want || host.endsWith("." + want))) return { error: `page is on ${host}` };
  const visible = (el) => el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
  const nameOf = (el) => {
    const by = (el.getAttribute("aria-labelledby") || "")
      .split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ");
    return (el.getAttribute("aria-label") || by || el.labels?.[0]?.innerText || el.placeholder || el.name || "")
      .replace(/\s+/g, " ").replace(/\s*\*$/, "").trim();
  };
  let hits = selector
    ? [...document.querySelectorAll(selector)]
    : [...document.querySelectorAll("input, textarea, select")].filter(
        (el) => nameOf(el).toLowerCase() === label.toLowerCase());
  hits = hits.filter(visible);
  if (hits.length !== 1) return { error: `${hits.length} visible fields match` };
  const el = hits[0];
  if (el.tagName === "SELECT") {
    const want = value.toLowerCase();
    const opts = [...el.options];
    const hit = opts.findIndex((o) => o.value.toLowerCase() === want);
    const idx = hit >= 0 ? hit : opts.findIndex((o) => o.text.trim().toLowerCase() === want);
    if (idx < 0) return { error: "no dropdown option matches" };
    el.focus();
    el.selectedIndex = idx;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return { label: nameOf(el), length: opts[idx].text.trim().length };
  }
  const proto = Object.getPrototypeOf(el);
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  if (!setter) return { error: "field has no value setter" };
  el.focus();
  setter.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  if (el.tagName !== "SELECT" && el.type !== "password") el.style.webkitTextSecurity = "disc";
  return { label: nameOf(el), length: el.value.length };
}

async function cdpEvaluate(wsUrl, expression) {
  const ws = new WebSocket(wsUrl);
  await new Promise((ok, fail) => {
    ws.onopen = ok;
    ws.onerror = () => fail(new Error("CDP websocket failed"));
  });
  const reply = new Promise((ok) => {
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.id === 1) ok(msg);
    };
  });
  ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { expression, returnByValue: true } }));
  const msg = await reply;
  ws.close();
  if (msg.error || msg.result?.exceptionDetails) throw new Error("page script failed");
  return msg.result.result.value;
}

function readSecret(handle) {
  let value;
  try {
    value = execFileSync("secret", ["exec", `NOMAD_FILL_VALUE=${handle}`, "--", "/bin/sh", "-c", 'printf %s "$NOMAD_FILL_VALUE"'],
      { stdio: ["ignore", "pipe", "ignore"], encoding: "utf8" });
  } catch {
    die(`secret ${handle} is not in the Keychain (operator: secret set ${handle})`);
  }
  if (!value) die(`secret ${handle} is empty`);
  return value;
}

async function main() {
  const a = args(process.argv.slice(2));
  if (a.verifyDate) {
    // One bit out: is the stored value a valid YYYY-MM-DD? Never the value itself.
    try { formatDate(readSecret(a.handle), "YYYY"); } catch (e) { die(e.message); }
    console.log(`ok: ${a.handle} is a valid YYYY-MM-DD date`);
    return;
  }
  const host = a.host.toLowerCase();

  try {
    execFileSync("python3", [join(HOOKS, "hostpolicy.py"), "check", a.handle, host], { stdio: ["ignore", "ignore", "pipe"] });
  } catch (e) {
    die(String(e.stderr || "host policy").trim().replace(/^refused: /, ""));
  }

  const targets = await (await fetch(`${CDP}/json/list`)).json();
  const tabs = targets.filter((t) => t.type === "page" && hostMatches(new URL(t.url).hostname, host));
  if (tabs.length !== 1) die(`${tabs.length} open tabs are on ${host}; need exactly one`);

  let value = readSecret(a.handle);
  if (a.format) {
    try { value = formatDate(value, a.format); } catch (e) { die(e.message); }
  }

  const expr = `(${pageFill})(${JSON.stringify(host)}, ${JSON.stringify(a.label || "")}, ${JSON.stringify(a.selector || "")}, ${JSON.stringify(value)})`;
  value = null;
  const res = await cdpEvaluate(tabs[0].webSocketDebuggerUrl, expr);
  if (!res || res.error) die(res?.error || "no result");

  mkdirSync(STATE, { recursive: true });
  const file = join(STATE, "fills.json");
  let log = [];
  try { log = JSON.parse(readFileSync(file, "utf8")); } catch {}
  log.push({ host, label: res.label, length: res.length, at: new Date().toISOString() });
  writeFileSync(file, JSON.stringify(log.slice(-50)));

  const how = a.format ? ` as ${a.format}` : "";
  console.log(`filled ${a.handle}${how} on ${host} into "${res.label}": ${res.length} chars`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch((e) => die(e.message));
}
