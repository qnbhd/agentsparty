import Link from 'next/link';
import { ThemeSwitch } from 'fumadocs-ui/layouts/shared/slots/theme-switch';
import { PythonCode } from './code';
import { CubeField } from './cube-field';

const QUICKSTART = `from agentsparty.agent import Agent
from agentsparty.protocol import Text, msg
from agentsparty.kernel.role import roles
from agentsparty.runtime import AgentRuntime

Writer, Reviewer = roles("Writer", "Reviewer")

proto = (
    msg[Writer, Reviewer] ( "Note", Text)
    >> msg[Reviewer, Writer] ( "Ack", Text)
).close()

writer = Agent(model, Writer, "send a short note", proto)
reviewer = Agent(model, Reviewer, "acknowledge it", proto)

trace = AgentRuntime(proto, [writer, reviewer]).run_sync()`;

export default function Home() {
  return (
    <main className="flex flex-col">
      <Hero />
    </main>
  );
}

function Hero() {
  return (
    <section className="agentsparty-hero relative isolate overflow-hidden">
      <CubeField />

      <header className="agentsparty-hero-header">
        <Link className="agentsparty-hero-brand" href="/">
          <span>agentsparty</span>
          <span className="agentsparty-hero-version">0.1.x</span>
        </Link>
        <nav className="agentsparty-hero-nav" aria-label="Primary navigation">
          <Link href="/docs">Docs</Link>
          <Link href="/docs/concepts/protocol-first">Protocols</Link>
          <a
            className="agentsparty-hero-github"
            href="https://github.com/qnbhd/agentsparty"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="square"
              aria-hidden
            >
              <path d="M7 17 17 7" />
              <path d="M8 7h9v9" />
            </svg>
          </a>
          <ThemeSwitch />
        </nav>
      </header>

      <div className="agentsparty-hero-spacer" aria-hidden />

      <div className="agentsparty-hero-content">
        <div className="agentsparty-hero-copy">
          <div className="agentsparty-hero-eyebrow">multiparty session types</div>
          <h1>
            The protocol owns control.
            <br />
            The model owns content.
          </h1>
          <p>
            <code>agentsparty</code> describes one typed global choreography between
            named roles, projects it onto every endpoint, and runs the session. A
            language model fills a typed payload or picks a declared branch —
            nothing else.
          </p>
        </div>

        <div className="agentsparty-hero-demo">
          <div className="agentsparty-hero-actions">
            <Link href="/docs">Read the docs</Link>
            <Link href="/docs/start/quickstart">Start in 10 seconds</Link>
          </div>
          <HeroCodePanel />
        </div>
      </div>

      <footer className="agentsparty-hero-footer">
        <div>
          <strong>pip install agentsparty</strong>
          <span>Python 3.10+</span>
        </div>
        <div>
          <strong>Typed payloads</strong>
          <span>Checked before the first model call</span>
        </div>
        <div>
          <strong>Endpoint projection</strong>
          <span>One global type, every role derived</span>
        </div>
        <div>
          <strong>Declared branching</strong>
          <span>The model chooses, never invents</span>
        </div>
      </footer>
    </section>
  );
}

function HeroCodePanel() {
  return (
    <figure className="agentsparty-hero-code">
      <figcaption>
        <span>quickstart.py</span>
        <span>python</span>
      </figcaption>
      <PythonCode code={QUICKSTART} />
    </figure>
  );
}
