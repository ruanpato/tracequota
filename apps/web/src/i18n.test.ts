// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Ruan Pato

import { afterEach, describe, expect, it } from "vitest";
import { catalogs, setPreferredLocale, supportedLocale, t } from "./i18n";
import { money, formatDateTime } from "./types";

afterEach(() => setPreferredLocale("en-US"));
describe("language catalogs and accounting semantics", () => {
  it("covers identical keys and interpolation parameters in both languages", () => {
    expect(Object.keys(catalogs["pt-BR"]).sort()).toEqual(
      Object.keys(catalogs["en-US"]).sort(),
    );
    for (const [key, english] of Object.entries(catalogs["en-US"])) {
      const portuguese = catalogs["pt-BR"][key];
      const variants = (message: typeof english) =>
        typeof message === "string" ? [message] : [message.one, message.other];
      const expected = variants(english).map((value) =>
        [...value.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
      );
      expect(
        variants(portuguese).map((value) =>
          [...value.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort(),
        ),
        key,
      ).toEqual(expected);
    }
  });
  it("handles plural forms and unknown runtime labels without crashing", () => {
    expect(t("{count} calls", { count: 1 }, "en-US")).toBe("1 call");
    expect(t("{count} calls", { count: 2 }, "pt-BR")).toBe("2 chamadas");
    expect(t("provider-defined label", {}, "pt-BR")).toBe(
      "provider-defined label",
    );
    expect(supportedLocale("fr-FR")).toBe("en-US");
  });
  it("localizes dates and amounts while retaining USD, UTC and unknown-versus-zero", () => {
    setPreferredLocale("pt-BR");
    expect(money(null)).toBe("Desconhecido");
    expect(money(0)).toMatch(/US\$.*0,00/);
    expect(money("22.05")).toMatch(/US\$.*22,05/);
    expect(formatDateTime("2026-09-28T08:00:00Z")).toContain("UTC");
    expect(formatDateTime("2026-09-28T08:00:00Z")).toContain("28 de set.");
    setPreferredLocale("en-US");
    expect(money(0)).toBe("$0.00");
  });
});
