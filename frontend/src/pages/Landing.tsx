import { useLayoutEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Hexagon, ChevronRight } from 'lucide-react';
import { BackgroundVideo } from '../components/BackgroundVideo';



// ─────────────────────────────────────────
// RevealBlock — fade-up on viewport enter
// ─────────────────────────────────────────
interface RevealProps {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}

const RevealBlock: React.FC<RevealProps> = ({ children, delay = 0, className = '' }) => {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); io.disconnect(); } },
      { threshold: 0.15 }
    );
    const raf = requestAnimationFrame(() => io.observe(el));
    return () => { cancelAnimationFrame(raf); io.disconnect(); };
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        willChange: 'transform, opacity',
        transform: visible ? 'translateY(0)' : 'translateY(2rem)',
        opacity: visible ? 1 : 0,
        transition: `transform 700ms ease-out ${delay}ms, opacity 700ms ease-out ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
};

// ─────────────────────────────────────────
// Glass helpers (inline to avoid Tailwind scan issues)
// ─────────────────────────────────────────
const glassPanel = {
  background: 'rgba(255,255,255,0.15)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
} as React.CSSProperties;

const glassBadge = (extra?: React.CSSProperties): React.CSSProperties => ({
  ...glassPanel,
  borderLeft: '2px solid #fff',
  paddingLeft: '0.75rem',
  paddingRight: '0.75rem',
  paddingTop: '0.375rem',
  paddingBottom: '0.375rem',
  ...extra,
});

const glassCta = {
  background: 'rgba(255,255,255,0.10)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  border: '1px solid rgba(255,255,255,0.25)',
} as React.CSSProperties;

const glassCapPanel = {
  background: 'rgba(255,255,255,0.10)',
  backdropFilter: 'blur(12px)',
  WebkitBackdropFilter: 'blur(12px)',
  border: '1px solid rgba(255,255,255,0.15)',
} as React.CSSProperties;

// ─────────────────────────────────────────
// APP
// ─────────────────────────────────────────
export default function App() {
  return (
    <div className="relative text-white" style={{ background: '#0a0a0a' }}>
      <BackgroundVideo interactiveScroll />

      {/* ══════════════════════════════════
          NAVBAR — fixed, z-50
      ══════════════════════════════════ */}
      <nav
        className="fixed top-0 left-0 w-full z-50 px-5 sm:px-8 md:px-12"
        style={{
          background: 'rgba(10,10,10,0.80)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          borderBottom: '1px solid rgba(255,255,255,0.15)',
        }}
      >
        <div className="max-w-[1440px] mx-auto flex items-center justify-between h-20">
          {/* Logo */}
          <RevealBlock delay={0} className="flex items-center gap-2">
            <Hexagon size={24} strokeWidth={1.5} />
            <span className="text-lg sm:text-xl font-medium tracking-tight lowercase">codementor</span>
          </RevealBlock>

          {/* Nav links (md+) */}
          <div className="hidden md:flex items-center gap-8 lg:gap-10">
            <RevealBlock delay={100}>
              <Link to="/problems" className="text-sm text-white/85 hover:text-white transition-colors duration-300">
                Problems
                <sup className="font-mono text-[10px] text-white/60 ml-0.5">120+</sup>
              </Link>
            </RevealBlock>
            <RevealBlock delay={200}>
              <Link to="/doubts" className="text-sm text-white/85 hover:text-white transition-colors duration-300">Doubt Board</Link>
            </RevealBlock>
            <RevealBlock delay={300}>
              <a href="#teachers" className="text-sm text-white/85 hover:text-white transition-colors duration-300">For Teachers</a>
            </RevealBlock>
            <RevealBlock delay={400}>
              <a href="#contact" className="text-sm text-white/85 hover:text-white transition-colors duration-300">Contact</a>
            </RevealBlock>
          </div>

          {/* CTA */}
          <RevealBlock delay={500}>
            <Link
              to="/signup"
              className="rounded-md px-4 py-2 text-xs sm:px-5 sm:text-sm text-white hover:bg-white/25 transition-all duration-300"
              style={{ ...glassPanel, border: '1px solid rgba(255,255,255,0.20)' }}
            >
              Start Practicing Free
            </Link>
          </RevealBlock>
        </div>
      </nav>

      {/* Content sits above the fixed video */}
      <div className="relative z-10">

        {/* ══════════════════════════════════
            SECTION ONE — HERO
        ══════════════════════════════════ */}
        <section className="min-h-screen supports-[height:100svh]:min-h-[100svh] flex flex-col justify-between px-5 sm:px-8 md:px-12 pt-24 sm:pt-28 pb-12 md:pb-16">

          {/* Top row */}
          <div className="flex flex-col gap-8 sm:flex-row justify-between items-start">
            {/* Left — service list */}
            <div className="flex flex-col gap-2">
              {['AUTOMATED CODE GRADING', 'AI-POWERED FEEDBACK', 'TEACHER-REVIEWED ANSWERS'].map(
                (s, i) => (
                  <RevealBlock key={s} delay={150 + i * 120}>
                    <p className="font-mono text-xs uppercase tracking-[0.15em] text-white/90 drop-shadow-md">
                      / {s}
                    </p>
                  </RevealBlock>
                )
              )}
            </div>

            {/* Right — intro */}
            <RevealBlock delay={300} className="max-w-xs sm:text-right">
              <p className="text-lg sm:text-xl leading-relaxed text-white drop-shadow-md">
                We built a practice platform that grades your code instantly, explains it like a
                mentor, and never lets an unreviewed AI answer reach you.
              </p>
            </RevealBlock>
          </div>

          {/* Bottom row */}
          <div className="flex flex-col gap-8 md:flex-row items-end justify-between">
            {/* Left — badge + H1 */}
            <div className="flex flex-col items-start">
              <RevealBlock delay={150}>
                <div
                  className="mb-5 font-mono text-[11px] uppercase tracking-[0.15em] text-white"
                  style={glassBadge()}
                >
                  Trusted by 100+ Classrooms
                </div>
              </RevealBlock>
              <RevealBlock delay={280}>
                <h1 className="text-5xl sm:text-6xl lg:text-7xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
                  Practice. Feedback.<br />
                  Mastery.
                </h1>
              </RevealBlock>
            </div>

            {/* Right — cool live sandbox indicator card */}
            <RevealBlock delay={420}>
              <div
                className="flex flex-col gap-3 rounded-2xl p-5 max-w-xs"
                style={{
                  ...glassPanel,
                  border: '1px solid rgba(255,255,255,0.20)',
                  boxShadow: '0 20px 40px -15px rgba(0,0,0,0.5)',
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                    </span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.20em] text-green-400 font-semibold">
                      SANDBOX v2.4 ONLINE
                    </span>
                  </div>
                  <span className="rounded-md bg-white/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-widest text-white/60">
                    60 FPS
                  </span>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-base font-semibold tracking-tight text-white">
                    Instant Code Intelligence
                  </span>
                  <p className="text-xs text-white/70 leading-relaxed">
                    Zero-latency containerized execution with real-time AI code analysis.
                  </p>
                </div>

                <Link
                  to="/signup"
                  className="mt-1 flex items-center justify-between rounded-full bg-white px-4 py-2 text-xs font-medium text-black hover:bg-white/85 transition-all duration-300 group"
                >
                  <span>Launch Practice Arena</span>
                  <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                </Link>
              </div>
            </RevealBlock>
          </div>
        </section>

        {/* 80vh spacer — gives scroll room to scrub video */}
        <div className="h-[80vh]" aria-hidden="true" />

        {/* ══════════════════════════════════
            SECTION TWO — CAPABILITY
        ══════════════════════════════════ */}
        <section className="min-h-screen supports-[height:100svh]:min-h-[100svh] flex flex-col justify-between px-5 sm:px-8 md:px-12 pt-12 pb-12 md:pb-16">

          {/* Top row */}
          <div className="flex flex-col gap-8 sm:flex-row justify-between items-start">
            {/* Left badge */}
            <RevealBlock delay={120}>
              <div
                className="font-mono text-[11px] uppercase tracking-[0.15em] text-white"
                style={glassBadge()}
              >
                Learn On Demand
              </div>
            </RevealBlock>

            {/* Right copy */}
            <RevealBlock delay={220} className="max-w-sm sm:text-right">
              <p className="text-lg sm:text-xl leading-relaxed text-white drop-shadow-md">
                Every submission gets a verdict, every doubt gets an answer — and nothing reaches
                you until it's been checked.
              </p>
            </RevealBlock>
          </div>

          {/* Bottom row */}
          <div className="flex flex-col md:flex-row items-end justify-between gap-16">

            {/* Left column — H2 + body + CTAs */}
            <div className="max-w-xl flex flex-col items-start">
              <RevealBlock delay={180}>
                <h2 className="text-5xl sm:text-6xl lg:text-7xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
                  Ship code<br />you understand.
                </h2>
              </RevealBlock>

              <RevealBlock delay={320}>
                <p className="mt-6 max-w-md text-sm sm:text-base text-white/80 drop-shadow-md leading-relaxed">
                  From your first submission to your hardest doubt, CodeMentor grades in a sandbox,
                  explains in plain language, and routes anything sensitive through a real teacher
                  before it ever reaches you.
                </p>
              </RevealBlock>

              <RevealBlock delay={420}>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Link
                    to="/problems"
                    className="flex items-center gap-1.5 rounded-full bg-white px-5 py-2.5 text-xs sm:text-sm font-medium text-black hover:bg-white/85 transition-all duration-300"
                  >
                    Try a problem <ChevronRight size={14} />
                  </Link>
                  <Link
                    to="/doubts"
                    className="rounded-full px-5 py-2.5 text-xs sm:text-sm text-white hover:bg-white/20 transition-all duration-300"
                    style={glassCta}
                  >
                    Talk to us
                  </Link>
                </div>
              </RevealBlock>
            </div>

            {/* Right — frosted capability panel */}
            <div className="w-full max-w-md rounded-2xl px-5 sm:px-6" style={glassCapPanel}>
              {[
                {
                  idx: '01',
                  title: 'Sandboxed grading',
                  body: 'Every submission runs in an isolated container, tested against hidden cases, no internet, no shared state.',
                },
                {
                  idx: '02',
                  title: 'AI code feedback',
                  body: 'Instant notes on readability, complexity, best practices, and optimization — not just pass/fail.',
                },
                {
                  idx: '03',
                  title: 'Teacher-checked doubts',
                  body: 'AI drafts an answer to every doubt, but a teacher reviews it before you ever see it.',
                },
              ].map((item, i, arr) => (
                <RevealBlock key={item.idx} delay={300 + i * 110}>
                  <div
                    className="group flex gap-5 py-5"
                    style={i < arr.length - 1 ? { borderBottom: '1px solid rgba(255,255,255,0.15)' } : {}}
                  >
                    <span className="font-mono text-[11px] tracking-[0.15em] text-white/55 mt-1 flex-shrink-0">
                      {item.idx}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-base sm:text-lg font-medium text-white">{item.title}</span>
                        <ChevronRight
                          size={16}
                          className="flex-shrink-0 text-white/40 transition-all duration-300 group-hover:translate-x-0.5 group-hover:text-white"
                        />
                      </div>
                      <p className="mt-1.5 text-sm leading-relaxed text-white/70">{item.body}</p>
                    </div>
                  </div>
                </RevealBlock>
              ))}
            </div>

          </div>
        </section>

      </div>
    </div>
  );
}
