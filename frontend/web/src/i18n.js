import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import english from "./locales/en/common.json";
import spanish from "./locales/es/common.json";
import french from "./locales/fr/common.json";
import italian from "./locales/it/common.json";
import chinese from "./locales/zh/common.json";
import german from "./locales/de/common.json";

const SUPPORTED_LANGUAGES = [
  "en",
  "es",
  "fr",
  "it",
  "zh",
  "de",
];

function getInitialLanguage() {
  const storedLanguage = localStorage.getItem(
    "clearpath_language"
  );

  if (SUPPORTED_LANGUAGES.includes(storedLanguage)) {
    return storedLanguage;
  }

  const browserLanguage = navigator.language
    .split("-")[0]
    .toLowerCase();

  if (SUPPORTED_LANGUAGES.includes(browserLanguage)) {
    return browserLanguage;
  }

  return "en";
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { common: english },
      es: { common: spanish },
      fr: { common: french },
      it: { common: italian },
      zh: { common: chinese },
      de: { common: german },
    },

    lng: getInitialLanguage(),
    fallbackLng: "en",
    defaultNS: "common",

    interpolation: {
      escapeValue: false,
    },

    react: {
      useSuspense: false,
    },
  });

export default i18n;