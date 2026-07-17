import "./About.css";

function About() {
  return (
    <main className="about-page">
      <section className="about-hero">
        <h1>
          Bridging the Communication and Accessibility Gaps in Global
          Healthcare Navigation.
        </h1>

        <div className="about-title-line" />

        <p>
          ClearPath was founded by a multi-disciplinary team of clinicians, data
          scientists, and designers. We recognized that navigating global
          healthcare isn't just about finding a facility — it's about
          understanding complex systems through the lens of clarity and trust.
          Our mission is to democratize healthcare intelligence, transforming
          opaque data into actionable, accessible guidance for everyone,
          anywhere.
        </p>
      </section>

      <section className="about-card-panel">
        <article className="about-card">
          <div className="about-icon blue-icon">⊙</div>
          <h2>Dynamic Transparency</h2>
          <p>
            We expose the underlying mechanics of healthcare routing, ensuring
            you see the why behind every recommendation. No black boxes, just
            clear, verifiable data pathways.
          </p>
        </article>

        <article className="about-card">
          <div className="about-icon blue-icon">◉</div>
          <h2>Localized Intelligence</h2>
          <p>
            Context is everything. Our algorithms adapt to regional nuances,
            translating global medical standards into locally relevant,
            culturally aware guidance you can act on.
          </p>
        </article>

        <article className="about-card">
          <div className="about-icon red-icon">▣</div>
          <h2>Privacy-First Architecture</h2>
          <p>
            Built on a foundation of absolute discretion. Your health queries
            are decoupled from personal identifiers using state-of-the-art
            cryptographic frameworks, guaranteeing anonymity.
          </p>
        </article>
      </section>
    </main>
  );
}

export default About;