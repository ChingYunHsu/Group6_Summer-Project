import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import "./UserGuide.css";

/*
 * Numbers and icons are language-agnostic, so they live here as static
 * config. Every piece of displayed text is pulled from the translation
 * file at render time via the labelKey/eyebrowKey/etc. fields below.
 */
const DOCUMENTATION_BLOCKS = [
  {
    id: "product-guide",
    i18nKey: "productGuide",
    cards: [
      { number: "01", icon: "☷", cardKey: "setPreferences" },
      { number: "02", icon: "♟", cardKey: "checkCrowds" },
      { number: "03", icon: "⚑", cardKey: "routeAndSave" },
    ],
  },
  {
    id: "privacy-policy",
    i18nKey: "privacyPolicy",
    cards: [
      { number: "01", icon: "▣", cardKey: "localMedicalData" },
      { number: "02", icon: "◌", cardKey: "limitedProfileSync" },
      { number: "03", icon: "⊙", cardKey: "transparentUsage" },
    ],
  },
  {
    id: "terms",
    i18nKey: "terms",
    cards: [
      { number: "01", icon: "!", cardKey: "emergencyUse" },
      { number: "02", icon: "⌖", cardKey: "routingAccuracy" },
      { number: "03", icon: "✓", cardKey: "responsibleUse" },
    ],
  },
];

function UserGuide() {
  const { t } = useTranslation("common");
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedBlockId = searchParams.get("section");

  const activeBlockId = useMemo(() => {
    const requestedBlockExists = DOCUMENTATION_BLOCKS.some(
      (block) => block.id === requestedBlockId
    );

    return requestedBlockExists ? requestedBlockId : "product-guide";
  }, [requestedBlockId]);

  const activeBlock = useMemo(() => {
    return (
      DOCUMENTATION_BLOCKS.find(
        (block) => block.id === activeBlockId
      ) || DOCUMENTATION_BLOCKS[0]
    );
  }, [activeBlockId]);

  function changeDocumentationBlock(blockId) {
    if (blockId === "product-guide") {
      setSearchParams({});
      return;
    }

    setSearchParams({ section: blockId });
  }

  return (
    <main className="guide-console-page">
      <aside className="guide-sidebar">
        <p>{t("userGuide.sidebarHeading")}</p>

        {DOCUMENTATION_BLOCKS.map((block) => (
          <button
            key={block.id}
            type="button"
            className={activeBlockId === block.id ? "active" : ""}
            onClick={() => changeDocumentationBlock(block.id)}
          >
            {t(`userGuide.blocks.${block.i18nKey}.label`)}
          </button>
        ))}
      </aside>

      <section className="guide-content">
        <p className="eyebrow-label">
          {t(`userGuide.blocks.${activeBlock.i18nKey}.eyebrow`)}
        </p>

        <h1>{t(`userGuide.blocks.${activeBlock.i18nKey}.title`)}</h1>

        <p className="guide-intro">
          {t(`userGuide.blocks.${activeBlock.i18nKey}.intro`)}
        </p>

        <section className="guide-step-grid">
          {activeBlock.cards.map((card) => (
            <article className="guide-step-card" key={card.cardKey}>
              <span className="guide-step-number">{card.number}</span>

              <div className="guide-step-icon">{card.icon}</div>

              <h2>
                {t(
                  `userGuide.blocks.${activeBlock.i18nKey}.cards.${card.cardKey}.title`
                )}
              </h2>
              <p>
                {t(
                  `userGuide.blocks.${activeBlock.i18nKey}.cards.${card.cardKey}.text`
                )}
              </p>
            </article>
          ))}
        </section>

        <section className="guide-compliance-card">
          <div className="guide-compliance-icon">▣</div>

          <div>
            <h2>
              {t(`userGuide.blocks.${activeBlock.i18nKey}.complianceTitle`)}
            </h2>
            <p>
              {t(`userGuide.blocks.${activeBlock.i18nKey}.complianceText`)}
            </p>

            <div className="guide-compliance-actions">
              <button
                type="button"
                onClick={() =>
                  changeDocumentationBlock("privacy-policy")
                }
              >
                {t("userGuide.reviewPrivacyPolicyCta")}
              </button>

              <button
                type="button"
                onClick={() => changeDocumentationBlock("terms")}
              >
                {t("userGuide.termsOfServiceCta")}
              </button>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

export default UserGuide;
