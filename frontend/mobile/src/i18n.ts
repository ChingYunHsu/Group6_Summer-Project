
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import de from "./locales/de/common.json";
import en from "./locales/en/common.json";
import es from "./locales/es/common.json";
import fr from "./locales/fr/common.json";
import it from "./locales/it/common.json";
import zh from "./locales/zh/common.json";

i18n.use(initReactI18next).init({
  compatibilityJSON: "v4",
  fallbackLng: "en",

  resources: {
    en: { translation: en },
    es: { translation: es },
    fr: { translation: fr },
    zh: { translation: zh },
    it: { translation: it },
    de: { translation: de },
  },

  interpolation: {
    escapeValue: false,
  },
});

export default i18n;