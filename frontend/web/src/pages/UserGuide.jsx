import { useMemo, useState } from "react";
import "./UserGuide.css";

const DOCUMENTATION_BLOCKS = [
  {
    id: "product-guide",
    label: "Product Guide",
    eyebrow: "DOCUMENTATION",
    title: "How To Use ClearPath",
    intro:
      "Master the core steps for using your healthcare intelligence dashboard. Follow these guidance blocks to configure preferences, monitor facility conditions, and access route support.",
    cards: [
      {
        number: "01",
        icon: "☷",
        title: "Set Preferences",
        text:
          "Configure notification thresholds, language needs, and accessibility priorities so ClearPath can surface the most relevant healthcare options.",
      },
      {
        number: "02",
        icon: "♟",
        title: "Check Crowds",
        text:
          "Use the live map and insights dashboard to monitor facility busyness, expected wait times, and operational flow across priority locations.",
      },
      {
        number: "03",
        icon: "⚑",
        title: "Route & Save",
        text:
          "Open a facility card, review its current status, save important locations, and launch directions when route support is needed.",
      },
    ],
    complianceTitle: "Data Integrity & Compliance",
    complianceText:
      "ClearPath operates with strict data minimization principles. Local storage is used for non-identifiable UI preferences, while sensitive clinical information should remain local to the traveller’s device unless an approved handoff flow is explicitly introduced.",
  },
  {
    id: "privacy-policy",
    label: "Privacy Policy",
    eyebrow: "PRIVACY",
    title: "Privacy Policy",
    intro:
      "ClearPath is designed around local-first handling of sensitive medical information and minimal exposure of personal data.",
    cards: [
      {
        number: "01",
        icon: "▣",
        title: "Local Medical Data",
        text:
          "Sensitive medical details should remain on the user’s device and should not be synced to the cloud database.",
      },
      {
        number: "02",
        icon: "◌",
        title: "Limited Profile Sync",
        text:
          "Non-clinical account fields may be used for interface personalization and standard account management.",
      },
      {
        number: "03",
        icon: "⊙",
        title: "Transparent Usage",
        text:
          "ClearPath should clearly communicate when location, saved facility, or preference data is being used by the interface.",
      },
    ],
    complianceTitle: "Privacy-First Handling",
    complianceText:
      "The system avoids unnecessary collection of sensitive healthcare data. Any future backend integration should preserve the separation between general account information and clinical profile information.",
  },
  {
    id: "terms",
    label: "Terms of Service",
    eyebrow: "TERMS",
    title: "Terms of Service",
    intro:
      "ClearPath provides healthcare navigation support and decision assistance, but it does not replace emergency services or professional medical advice.",
    cards: [
      {
        number: "01",
        icon: "!",
        title: "Emergency Use",
        text:
          "In an emergency, users should contact local emergency services immediately rather than relying only on app guidance.",
      },
      {
        number: "02",
        icon: "⌖",
        title: "Routing Accuracy",
        text:
          "Directions, wait times, and facility status information are guidance signals and may change in real time.",
      },
      {
        number: "03",
        icon: "✓",
        title: "Responsible Use",
        text:
          "Users should verify critical healthcare information directly with providers where possible.",
      },
    ],
    complianceTitle: "Service Boundaries",
    complianceText:
      "ClearPath is a support tool for accessibility-aware healthcare navigation. It should be presented as informational guidance, not as a clinical diagnosis, medical instruction system, or emergency dispatch service.",
  },
];

function UserGuide() {
  const [activeBlockId, setActiveBlockId] = useState("product-guide");

  const activeBlock = useMemo(() => {
    return (
      DOCUMENTATION_BLOCKS.find((block) => block.id === activeBlockId) ||
      DOCUMENTATION_BLOCKS[0]
    );
  }, [activeBlockId]);

  return (
    <main className="guide-console-page">
      <aside className="guide-sidebar">
        <p>DOCUMENTATION</p>

        {DOCUMENTATION_BLOCKS.map((block) => (
          <button
            key={block.id}
            type="button"
            className={activeBlockId === block.id ? "active" : ""}
            onClick={() => setActiveBlockId(block.id)}
          >
            {block.label}
          </button>
        ))}
      </aside>

      <section className="guide-content">
        <p className="eyebrow-label">{activeBlock.eyebrow}</p>

        <h1>{activeBlock.title}</h1>

        <p className="guide-intro">{activeBlock.intro}</p>

        <section className="guide-step-grid">
          {activeBlock.cards.map((card) => (
            <article className="guide-step-card" key={card.title}>
              <span className="guide-step-number">{card.number}</span>

              <div className="guide-step-icon">{card.icon}</div>

              <h2>{card.title}</h2>
              <p>{card.text}</p>
            </article>
          ))}
        </section>

        <section className="guide-compliance-card">
          <div className="guide-compliance-icon">▣</div>

          <div>
            <h2>{activeBlock.complianceTitle}</h2>
            <p>{activeBlock.complianceText}</p>

            <div className="guide-compliance-actions">
              <button
                type="button"
                onClick={() => setActiveBlockId("privacy-policy")}
              >
                Review Privacy Policy
              </button>

              <button type="button" onClick={() => setActiveBlockId("terms")}>
                Terms of Service
              </button>
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

export default UserGuide;