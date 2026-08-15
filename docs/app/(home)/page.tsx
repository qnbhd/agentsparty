import Link from 'next/link';
import { HeroShader } from './hero-shader';
import { InstallRail } from './install-rail';

export default function Home() {
  return (
    <main className="flex flex-col">
      <Hero />
    </main>
  );
}

function Hero() {
  return (
    <section className="agentsparty-hero">
      <HeroShader />
      {/* Darkens the middle of the field so the headline keeps its contrast
       * while the edges stay bright. */}
      <div className="agentsparty-hero-vignette" aria-hidden />

      <div className="agentsparty-hero-content">
        <div className="agentsparty-hero-badge">
          <span>agentsparty</span>
          <span>0.1.x</span>
        </div>

        <h1>The protocol owns control. The model owns content.</h1>

        <div className="agentsparty-hero-actions">
          <Link className="agentsparty-pill" href="/docs">
            Docs
          </Link>
          <Link className="agentsparty-pill agentsparty-pill-accent" href="/docs/start/quickstart">
            Start in 10 seconds
          </Link>
          <a
            className="agentsparty-pill agentsparty-pill-icon"
            href="https://github.com/qnbhd/agentsparty"
            target="_blank"
            rel="noreferrer"
            aria-label="GitHub"
          >
            <GitHubMark />
          </a>
        </div>

        <InstallRail />
      </div>
    </section>
  );
}

function GitHubMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 .5C5.7.5.6 5.6.6 11.9c0 5 3.3 9.3 7.8 10.8.6.1.8-.2.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.1.1 1.7 1.2 1.7 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.8 0-1.3.5-2.3 1.2-3.2-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.9 1.2 1.9 1.2 3.2 0 4.5-2.7 5.5-5.3 5.8.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6a11.4 11.4 0 0 0 7.8-10.8C23.4 5.6 18.3.5 12 .5Z" />
    </svg>
  );
}
