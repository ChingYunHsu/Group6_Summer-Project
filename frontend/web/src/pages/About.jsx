import { useTranslation } from "react-i18next";
import "./About.css";

function About() {
  const { t } = useTranslation("common");

  return (
    <main className="about-page">
      <section className="about-hero">
        <h1>{t("about.hero.title")}</h1>

        <div className="about-title-line" />

        <p>{t("about.hero.description")}</p>
      </section>

      <section className="about-card-panel">
        <article className="about-card">
          <div className="about-icon blue-icon">⊙</div>
          <h2>{t("about.cards.transparency.title")}</h2>
          <p>{t("about.cards.transparency.description")}</p>
        </article>

        <article className="about-card">
          <div className="about-icon blue-icon">◉</div>
          <h2>{t("about.cards.localizedIntelligence.title")}</h2>
          <p>{t("about.cards.localizedIntelligence.description")}</p>
        </article>

        <article className="about-card">
          <div className="about-icon red-icon">▣</div>
          <h2>{t("about.cards.privacy.title")}</h2>
          <p>{t("about.cards.privacy.description")}</p>
        </article>
      </section>
    </main>
  );
}

export default About;
