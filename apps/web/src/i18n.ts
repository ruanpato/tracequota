// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Ruan Pato

import english from "./locales/en-US.json";
import portuguese from "./locales/pt-BR.json";

export type Locale = "en-US" | "pt-BR";
type Message = string | { one: string; other: string };
export const catalogs: Record<Locale, Record<string, Message>> = {
  "en-US": english,
  "pt-BR": portuguese,
};
export function supportedLocale(value: string | null): Locale {
  return value === "pt-BR" ? value : "en-US";
}
function initialLocale(): Locale {
  try {
    return supportedLocale(localStorage.getItem("tracequota-locale"));
  } catch {
    return "en-US";
  }
}
let preferredLocale = initialLocale();
export const getLocale = () => preferredLocale;
export function setPreferredLocale(locale: Locale): void {
  preferredLocale = supportedLocale(locale);
  try {
    localStorage.setItem("tracequota-locale", preferredLocale);
  } catch {
    // Language switching still works when browser storage is unavailable.
  }
}
export function t(
  key: string,
  values: Record<string, string | number> = {},
  locale: Locale = getLocale(),
): string {
  const message = catalogs[locale][key] ?? catalogs["en-US"][key] ?? key;
  const template =
    typeof message === "string"
      ? message
      : new Intl.PluralRules(locale).select(Number(values.count)) === "one"
        ? message.one
        : message.other;
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    values[name] === undefined
      ? match
      : typeof values[name] === "number"
        ? new Intl.NumberFormat(locale).format(values[name])
        : String(values[name]),
  );
}
