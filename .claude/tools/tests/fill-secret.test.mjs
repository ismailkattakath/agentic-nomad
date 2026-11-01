// node --test .claude/tools/tests — offline, no browser, no Keychain. Run by the flake's project gate.
import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDate, hostMatches } from "../fill-secret.mjs";

test("formatDate splits and re-lays a YYYY-MM-DD expiry", () => {
  const v = "2030-03-04";
  const cases = {
    DD: "04", D: "4", MM: "03", M: "3", MMM: "Mar", MMMM: "March", YYYY: "2030", YY: "30",
    "DD/MM/YYYY": "04/03/2030", "MM/YY": "03/30", "D MMMM YYYY": "4 March 2030",
  };
  for (const [fmt, want] of Object.entries(cases)) assert.equal(formatDate(v, fmt), want, fmt);
  assert.equal(formatDate("2030-12-31", "MMM"), "Dec");
});

test("formatDate refuses a non-date and never echoes the value", () => {
  for (const bad of ["X0000000", "2030/03/04", "2030-13-01", "2030-00-10", "2030-03-32"]) {
    assert.throws(() => formatDate(bad, "DD"), (e) => !e.message.includes(bad), bad);
  }
});

test("hostMatches is exact-or-subdomain only", () => {
  assert.ok(hostMatches("identity.airline.example", "airline.example"));
  assert.ok(hostMatches("airline.example.", "airline.example"));
  assert.ok(!hostMatches("evilairline.example", "airline.example"));
  assert.ok(!hostMatches("airline.example.evil.example", "airline.example"));
  assert.ok(!hostMatches("", "airline.example"));
});
