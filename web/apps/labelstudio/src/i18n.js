import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import { en_US } from './locales/en/en-US.js';
import { zh_CN } from './locales/zh/zh-CN.js';

const resources = {
  'en-US': en_US,
  'zh-CN': zh_CN,
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: ["en-US", "zh-CN"],
    supportedLngs: ["en-US", "zh-CN"],
    debug: false,
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
