"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

// ─── Font injection ───────────────────────────────────────────────────────────
function FontLoader() {
  useEffect(() => {
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap";
    document.head.appendChild(link);
  }, []);
  return null;
}

// ─── Orbital compliance visualization ────────────────────────────────────────
function OrbitalCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf: number;
    let t = 0;

    type Node = {
      label: string;
      orbit: number;
      speed: number;
      phase: number;
      size: number;
      color: string;
    };

    const nodes: Node[] = [
      { label: "REGULATIONS", orbit: 290, speed: 0.00022, phase: 0,           size: 7,  color: "rgba(96,165,250,0.9)"  },
      { label: "CONTROLS",    orbit: 215, speed: 0.00038, phase: Math.PI/2.5, size: 6,  color: "rgba(147,197,253,0.8)" },
      { label: "EVIDENCE",    orbit: 250, speed: 0.00028, phase: Math.PI,     size: 6,  color: "rgba(96,165,250,0.8)"  },
      { label: "AUDIT",       orbit: 165, speed: 0.00055, phase: Math.PI*1.4, size: 9,  color: "rgba(59,130,246,1)"    },
      { label: "FINDINGS",    orbit: 272, speed: 0.00019, phase: Math.PI*0.7, size: 6,  color: "rgba(147,197,253,0.7)" },
      { label: "REMEDIATION", orbit: 190, speed: 0.00045, phase: Math.PI*1.8, size: 6,  color: "rgba(96,165,250,0.75)" },
      { label: "REPORTS",     orbit: 135, speed: 0.00068, phase: Math.PI*1.1, size: 5,  color: "rgba(59,130,246,0.85)" },
    ];

    const resize = () => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    const draw = () => {
      if (!ctx || !canvas) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width * 0.62;
      const cy = canvas.height * 0.5;
      t++;

      // Draw orbit rings
      nodes.forEach((n) => {
        ctx.beginPath();
        ctx.arc(cx, cy, n.orbit, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(255,255,255,0.04)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Compute positions
      const positions = nodes.map((n) => ({
        x: cx + Math.cos(t * n.speed + n.phase) * n.orbit,
        y: cy + Math.sin(t * n.speed + n.phase) * n.orbit,
        ...n,
      }));

      // Draw spoke lines (node → center)
      positions.forEach((p) => {
        const grad = ctx.createLinearGradient(p.x, p.y, cx, cy);
        grad.addColorStop(0, "rgba(59,130,246,0.3)");
        grad.addColorStop(1, "rgba(59,130,246,0.0)");
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(cx, cy);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      });

      // Cross-connections for close nodes
      for (let i = 0; i < positions.length; i++) {
        for (let j = i + 1; j < positions.length; j++) {
          const dx = positions[i].x - positions[j].x;
          const dy = positions[i].y - positions[j].y;
          const d  = Math.sqrt(dx * dx + dy * dy);
          if (d < 130) {
            ctx.beginPath();
            ctx.moveTo(positions[i].x, positions[i].y);
            ctx.lineTo(positions[j].x, positions[j].y);
            ctx.strokeStyle = `rgba(59,130,246,${0.18 * (1 - d / 90)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      // Draw center hub
      const hubPulse = 0.85 + 0.15 * Math.sin(t * 0.03);
      const hubGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 48 * hubPulse);
      hubGrad.addColorStop(0, "rgba(59,130,246,0.5)");
      hubGrad.addColorStop(1, "rgba(59,130,246,0)");
      ctx.beginPath();
      ctx.arc(cx, cy, 48 * hubPulse, 0, Math.PI * 2);
      ctx.fillStyle = hubGrad;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(cx, cy, 18, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(59,130,246,0.9)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(cx, cy, 9, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.fill();

      // Draw nodes + labels
      positions.forEach((p) => {
        // Node glow
        const glow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 4);
        glow.addColorStop(0, p.color.replace(/[\d.]+\)$/, "0.25)"));
        glow.addColorStop(1, "transparent");
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 4, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // Node dot
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();

        // Label
        ctx.font = "600 11px 'DM Sans', system-ui, sans-serif";
        ctx.letterSpacing = "0.1em";
        ctx.fillStyle = "rgba(148,163,184,0.8)";
        ctx.textAlign = "center";
        const lx = p.x;
        const ly = p.y + (p.y > cy ? p.size + 16 : -(p.size + 8));
        ctx.fillText(p.label, lx, ly);
      });

      raf = requestAnimationFrame(draw);
    };

    resize();
    draw();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, []);

  return (
    <canvas
      ref={ref}
      style={{ position: "absolute", inset: 0, width: "100%", height: "100%", display: "block" }}
    />
  );
}

// ─── Animated pipeline ────────────────────────────────────────────────────────
function PipelineFlow() {
  const stages = ["Intake", "Controls", "Evidence", "Audit", "Verdict", "Findings", "Remediation", "Export"];

  return (
    <div style={{ position: "relative", overflowX: "auto", paddingBottom: 8 }}>
      <style>{`
        @keyframes flowPulse {
          0%   { stroke-dashoffset: 60; opacity: 0; }
          20%  { opacity: 1; }
          80%  { opacity: 1; }
          100% { stroke-dashoffset: 0; opacity: 0; }
        }
        @keyframes nodePulse {
          0%, 100% { r: 5; opacity: 0.7; }
          50%       { r: 7; opacity: 1; }
        }
        @keyframes labelIn {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .pipeline-stage {
          transition: border-color 0.25s, background 0.25s;
        }
        .pipeline-stage:hover {
          border-color: rgba(59,130,246,0.5) !important;
          background: rgba(59,130,246,0.07) !important;
        }
      `}</style>

      <div style={{ display: "flex", alignItems: "center", gap: 0, minWidth: "max-content" }}>
        {stages.map((stage, i) => (
          <div key={stage} style={{ display: "flex", alignItems: "center" }}>
            <div
              className="pipeline-stage"
              style={{
                padding: "12px 20px",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 4,
                background: "rgba(255,255,255,0.03)",
                minWidth: 110,
                cursor: "default",
              }}
            >
              <div style={{ fontSize: 10, fontWeight: 600, color: "rgba(59,130,246,0.8)", letterSpacing: "0.08em", marginBottom: 6, fontFamily: "monospace" }}>
                {String(i + 1).padStart(2, "0")}
              </div>
              <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.75)" }}>{stage}</div>
            </div>
            {i < stages.length - 1 && (
              <div style={{ position: "relative", width: 32, height: 2, background: "rgba(255,255,255,0.06)", flexShrink: 0 }}>
                <div style={{
                  position: "absolute",
                  inset: 0,
                  background: "linear-gradient(90deg, rgba(59,130,246,0.8), rgba(59,130,246,0))",
                  animation: `flowPulse ${2.4 + i * 0.3}s ease-in-out ${i * 0.4}s infinite`,
                  animationFillMode: "both",
                  borderRadius: 2,
                }} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Regulatory ticker ────────────────────────────────────────────────────────
function RegTicker() {
  const items = [
    "FCA · UK", "FinCEN · US", "MAS · SG", "DFSA · UAE", "ASIC · AU",
    "ESMA · EU", "GDPR · EU", "SFC · HK", "SEBI · IN", "OSC · CA",
    "FCA · UK", "FinCEN · US", "MAS · SG", "DFSA · UAE", "ASIC · AU",
    "ESMA · EU", "GDPR · EU", "SFC · HK", "SEBI · IN", "OSC · CA",
  ];

  return (
    <div style={{ overflow: "hidden", borderTop: "1px solid rgba(255,255,255,0.07)", borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "14px 0", background: "rgba(255,255,255,0.02)" }}>
      <style>{`
        @keyframes ticker {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
      `}</style>
      <div style={{ display: "flex", animation: "ticker 28s linear infinite", width: "max-content" }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 28, marginRight: 28 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(148,163,184,0.5)", letterSpacing: "0.12em", textTransform: "uppercase", whiteSpace: "nowrap" }}>
              {item}
            </span>
            <span style={{ width: 3, height: 3, borderRadius: "50%", background: "rgba(59,130,246,0.4)", display: "inline-block", flexShrink: 0 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Animated count stat ──────────────────────────────────────────────────────
function BigStat({ value, label, note }: { value: string; label: string; note?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVisible(true); obs.disconnect(); }
    }, { threshold: 0.4 });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ transition: "opacity 1s, transform 1s", opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(20px)" }}>
      <div style={{
        fontFamily: "'DM Serif Display', Georgia, serif",
        fontSize: "clamp(52px, 6vw, 80px)",
        fontWeight: 400,
        color: "white",
        letterSpacing: "-0.02em",
        lineHeight: 1,
      }}>
        {value}
      </div>
      <div style={{ fontSize: 13, fontWeight: 500, color: "rgba(255,255,255,0.4)", marginTop: 12, textTransform: "uppercase", letterSpacing: "0.1em" }}>
        {label}
      </div>
      {note && (
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginTop: 6 }}>{note}</div>
      )}
    </div>
  );
}

// ─── Reveal hook ─────────────────────────────────────────────────────────────
function useReveal() {
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          const el = e.target as HTMLElement;
          el.style.opacity = "1";
          el.style.transform = "none";
        }
      });
    }, { threshold: 0.06 });
    document.querySelectorAll("[data-r]").forEach((el) => {
      const h = el as HTMLElement;
      const delay = h.dataset.delay || "0";
      h.style.opacity = "0";
      h.style.transform = "translateY(36px)";
      h.style.transition = `opacity 0.9s cubic-bezier(0.22,1,0.36,1) ${delay}ms, transform 0.9s cubic-bezier(0.22,1,0.36,1) ${delay}ms`;
      obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  useReveal();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  const serif = "'DM Serif Display', Georgia, 'Times New Roman', serif";
  const sans  = "'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

  return (
    <div style={{ fontFamily: sans, background: "#F9F9F7", overflowX: "hidden" }}>
      <FontLoader />

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::selection { background: rgba(59,130,246,0.25); }
        @keyframes fadeUp {
          from { opacity:0; transform:translateY(20px); }
          to   { opacity:1; transform:none; }
        }
        .nav-link { color:rgba(255,255,255,0.48); text-decoration:none; font-size:13px; font-weight:500; letter-spacing:0.01em; transition:color 0.2s; }
        .nav-link:hover { color:rgba(255,255,255,0.9); }
        .btn-primary {
          display:inline-flex; align-items:center; gap:10px;
          background:white; color:#0A0A0F; padding:13px 26px;
          border-radius:3px; font-size:14px; font-weight:600; text-decoration:none;
          letter-spacing:0.01em; transition:opacity 0.2s; font-family:inherit;
        }
        .btn-primary:hover { opacity:0.88; }
        .btn-ghost {
          display:inline-flex; align-items:center; gap:8px;
          border:1px solid rgba(255,255,255,0.18); color:rgba(255,255,255,0.6);
          padding:13px 26px; border-radius:3px; font-size:14px; font-weight:500;
          text-decoration:none; transition:border-color 0.2s, color 0.2s; font-family:inherit;
        }
        .btn-ghost:hover { border-color:rgba(255,255,255,0.4); color:white; }
        .dark-card {
          border:1px solid rgba(255,255,255,0.07); padding:28px 24px;
          transition:border-color 0.25s, background 0.25s; cursor:default;
        }
        .dark-card:hover { border-color:rgba(59,130,246,0.3); background:rgba(59,130,246,0.06); }
        .light-card {
          border:1px solid #E8E8E4; padding:28px 24px; background:white;
          transition:border-color 0.25s, box-shadow 0.25s; cursor:default;
        }
        .light-card:hover { border-color:#BFDBFE; box-shadow:0 6px 32px rgba(30,64,175,0.07); }
      `}</style>

      {/* ── NAV ──────────────────────────────────────────────────────────────── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
        background: scrolled ? "rgba(10, 10, 15, 0.94)" : "transparent",
        backdropFilter: scrolled ? "blur(24px)" : "none",
        WebkitBackdropFilter: scrolled ? "blur(24px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(255,255,255,0.06)" : "none",
        transition: "background 0.4s, border-color 0.4s, padding 0.3s",
        padding: scrolled ? "14px 0" : "24px 0",
      }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 40px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 2L18 7V13L10 18L2 13V7L10 2Z" stroke="rgba(59,130,246,0.9)" strokeWidth="1.2" fill="rgba(59,130,246,0.12)" />
              <circle cx="10" cy="10" r="2.5" fill="rgba(59,130,246,0.9)" />
            </svg>
            <span style={{ fontFamily: sans, color: "white", fontWeight: 600, fontSize: 14, letterSpacing: "0.08em", textTransform: "uppercase" }}>
              Tenet
            </span>
          </div>

          <div style={{ display: "flex", gap: 36 }}>
            {["Platform", "Solutions", "Coverage", "Company"].map((l) => (
              <a key={l} href="#" className="nav-link">{l}</a>
            ))}
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <Link href="/dashboard" style={{ color: "rgba(255,255,255,0.45)", textDecoration: "none", fontSize: 13, fontWeight: 500 }}>
              Sign in
            </Link>
            <a href="#demo" style={{
              background: "rgba(59,130,246,0.9)", color: "white", padding: "9px 20px",
              borderRadius: 3, fontSize: 13, fontWeight: 600, textDecoration: "none",
              letterSpacing: "0.02em", transition: "background 0.2s",
            }}
              onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "rgba(37,99,235,1)"}
              onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "rgba(59,130,246,0.9)"}>
              Request Demo
            </a>
          </div>
        </div>
      </nav>

      {/* ── HERO ─────────────────────────────────────────────────────────────── */}
      <section style={{ position: "relative", minHeight: "100vh", background: "#0A0A0F", display: "flex", alignItems: "center", overflow: "hidden" }}>
        <OrbitalCanvas />

        {/* Gradient vignette */}
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 55% 80% at 15% 50%, rgba(10,10,15,0.98) 0%, rgba(10,10,15,0.7) 45%, transparent 75%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 200, background: "linear-gradient(to top, #0A0A0F, transparent)", pointerEvents: "none" }} />

        <div style={{ position: "relative", maxWidth: 1280, margin: "0 auto", padding: "140px 40px 100px", width: "100%" }}>
          <div style={{ maxWidth: 600 }}>

            {/* Eyebrow */}
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 10,
              marginBottom: 40, animation: "fadeUp 0.8s ease both",
            }}>
              <span style={{ width: 24, height: 1, background: "rgba(59,130,246,0.7)", display: "block" }} />
              <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(59,130,246,0.8)", letterSpacing: "0.14em", textTransform: "uppercase" }}>
                Compliance Intelligence Platform
              </span>
            </div>

            {/* Headline */}
            <h1 style={{
              fontFamily: serif,
              fontSize: "clamp(46px, 5.5vw, 72px)",
              fontWeight: 400,
              lineHeight: 1.08,
              letterSpacing: "-0.01em",
              color: "white",
              margin: "0 0 28px",
              animation: "fadeUp 0.9s ease 0.1s both",
            }}>
              The operating system<br />
              <em style={{ fontStyle: "italic", color: "rgba(96,165,250,0.9)" }}>for modern compliance.</em>
            </h1>

            {/* Sub */}
            <p style={{
              fontFamily: sans,
              fontSize: 20,
              lineHeight: 1.65,
              color: "rgba(255,255,255,0.42)",
              margin: "0 0 48px",
              maxWidth: 480,
              fontWeight: 300,
              letterSpacing: "-0.01em",
              animation: "fadeUp 1s ease 0.2s both",
            }}>
              Regulations mapped to controls. Findings grounded in evidence. Outputs that regulators, auditors, and boards can trust.
            </p>

            {/* CTAs */}
            <div style={{ display: "flex", gap: 12, alignItems: "center", animation: "fadeUp 1s ease 0.3s both" }}>
              <a href="#demo" className="btn-primary">
                Request Demo
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </a>
              <a href="#platform" className="btn-ghost">
                Explore Platform
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── TICKER ───────────────────────────────────────────────────────────── */}
      <div style={{ background: "#0A0A0F" }}>
        <RegTicker />
      </div>

      {/* ── MISSION ──────────────────────────────────────────────────────────── */}
      <section style={{ background: "#F9F9F7", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 100 }}>

            <div style={{ paddingTop: 8 }} data-r>
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#888", display: "block" }}>
                Why Tenet
              </span>
            </div>

            <div data-r data-delay="80">
              <h2 style={{
                fontFamily: serif,
                fontSize: "clamp(34px, 3.5vw, 52px)",
                fontWeight: 400,
                lineHeight: 1.12,
                letterSpacing: "-0.01em",
                color: "#0A0A0F",
                margin: "0 0 36px",
              }}>
                Compliance is broken.<br />
                <em style={{ fontStyle: "italic", color: "#1E40AF" }}>Tenet fixes it structurally.</em>
              </h2>
              <p style={{ fontSize: 22, lineHeight: 1.65, color: "#444", maxWidth: 580, marginBottom: 24, fontWeight: 300, letterSpacing: "-0.01em" }}>
                Compliance has become a fragmented exercise in spreadsheets and manual effort — disconnected tools, inconsistent evidence, reports that fail scrutiny.
              </p>
              <p style={{ fontSize: 22, lineHeight: 1.65, color: "#444", maxWidth: 580, fontWeight: 300, letterSpacing: "-0.01em" }}>
                Tenet is not an AI chatbot. It is a deterministic compliance operating system — grounded in evidence, built for regulators.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── PLATFORM ─────────────────────────────────────────────────────────── */}
      <section id="platform" style={{ background: "#0D0D14", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "end", marginBottom: 80 }} data-r>
            <h2 style={{
              fontFamily: serif,
              fontSize: "clamp(32px, 3.2vw, 48px)",
              fontWeight: 400,
              lineHeight: 1.12,
              color: "white",
              letterSpacing: "-0.01em",
            }}>
              One system.<br />Every compliance workflow.
            </h2>
            <p style={{ fontSize: 20, lineHeight: 1.6, color: "rgba(255,255,255,0.45)", fontWeight: 300, maxWidth: 400, letterSpacing: "-0.01em" }}>
              From regulatory intake to regulator-ready export. No gaps. No ambiguity.
            </p>
          </div>

          {/* Pipeline animation */}
          <div data-r data-delay="100">
            <PipelineFlow />
          </div>

          {/* 8-pillar grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2, marginTop: 2 }} data-r data-delay="200">
            {[
              { n: "01", t: "Intake",         d: "Structured audit setup across jurisdictions, regimes, and entity types." },
              { n: "02", t: "Controls",        d: "Global control library mapped directly to regulatory frameworks." },
              { n: "03", t: "Evidence",        d: "Document ingestion, extraction, and evidence scoring against controls." },
              { n: "04", t: "Audit Reasoning", d: "Deterministic verdict engine. No hallucinations. No vague summaries." },
              { n: "05", t: "Findings",        d: "Structured, prioritised findings with severity triage and citations." },
              { n: "06", t: "Remediation",     d: "Tracked workflows with owners, due dates, and release-blocking flags." },
              { n: "07", t: "Reporting",       d: "Regulator-ready reports with export packages and audit trail." },
              { n: "08", t: "Monitoring",      d: "Continuous regulatory alert stream and obligation calendar." },
            ].map(({ n, t, d }) => (
              <div key={n} className="dark-card" style={{ background: "rgba(255,255,255,0.03)" }}>
                <div style={{ fontFamily: "monospace", fontSize: 10, fontWeight: 700, color: "rgba(59,130,246,0.7)", letterSpacing: "0.1em", marginBottom: 16 }}>{n}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "white", marginBottom: 10, letterSpacing: "-0.01em" }}>{t}</div>
                <div style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", lineHeight: 1.7, fontWeight: 300 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── REASONING ────────────────────────────────────────────────────────── */}
      <section style={{ background: "#F9F9F7", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 100 }}>

            <div data-r>
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#888", display: "block", marginBottom: 24 }}>
                Reasoning Engine
              </span>
              <h2 style={{ fontFamily: serif, fontSize: "clamp(32px, 3.2vw, 46px)", fontWeight: 400, lineHeight: 1.12, color: "#0A0A0F", letterSpacing: "-0.01em", marginBottom: 28 }}>
                Deterministic.<br /><em style={{ fontStyle: "italic", color: "#1E40AF" }}>Not probabilistic.</em>
              </h2>
              <p style={{ fontSize: 21, lineHeight: 1.6, color: "#444", fontWeight: 300, marginBottom: 40, maxWidth: 440, letterSpacing: "-0.01em" }}>
                Every verdict is grounded in evidence, mapped to a control, derived from a regulation. Fully reviewable. No black boxes.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {[
                  ["Deterministic verdict core", "across all controls and regimes"],
                  ["Evidence-grounded outputs", "every finding cites its source document"],
                  ["Human-reviewable reasoning", "full audit chain, no opaque AI decisions"],
                  ["Reusable control libraries", "portable across jurisdictions and frameworks"],
                  ["Immutable export discipline", "for regulatory submission and sign-off"],
                ].map(([title, desc]) => (
                  <div key={title} style={{ display: "flex", gap: 16, paddingBottom: 20, borderBottom: "1px solid #EAEAE6" }}>
                    <div style={{ width: 1, background: "rgba(59,130,246,0.4)", flexShrink: 0, minHeight: 40 }} />
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#0A0A0F", marginBottom: 3 }}>{title}</div>
                      <div style={{ fontSize: 13, color: "#888", fontWeight: 300 }}>{desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Audit log visual */}
            <div data-r data-delay="120">
              <div style={{ background: "#0D0D14", borderRadius: 6, padding: "28px", fontFamily: "monospace" }}>
                <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
                  {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
                    <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.7 }} />
                  ))}
                </div>

                {[
                  { ts: "14:22:01", type: "REGULATION",  msg: "FCA SYSC 6.1.1 — AML obligation identified",    ok: true  },
                  { ts: "14:22:01", type: "CONTROL",     msg: "CTL-AML-003 mapped to obligation",               ok: true  },
                  { ts: "14:22:02", type: "EVIDENCE",    msg: "AML_Policy_v4.pdf — indexed (94 pages)",         ok: true  },
                  { ts: "14:22:03", type: "SCORE",       msg: "Evidence gap: Transaction monitoring threshold",  ok: false },
                  { ts: "14:22:03", type: "VERDICT",     msg: "Control CTL-AML-003 → PARTIAL",                  ok: false },
                  { ts: "14:22:04", type: "FINDING",     msg: "F-2024-0142 generated — severity: HIGH",         ok: false },
                  { ts: "14:22:04", type: "REMEDIATION", msg: "REM-0089 created — due 2026-04-15",              ok: null  },
                  { ts: "14:22:05", type: "EXPORT",      msg: "Report package sealed — SHA-256 hash stored",    ok: true  },
                ].map(({ ts, type, msg, ok }, i) => (
                  <div key={i} style={{
                    display: "flex", gap: 14, padding: "8px 0",
                    borderBottom: "1px solid rgba(255,255,255,0.04)",
                    animation: `fadeUp 0.5s ease ${i * 0.08}s both`,
                  }}>
                    <span style={{ fontSize: 10, color: "rgba(255,255,255,0.2)", flexShrink: 0, paddingTop: 2 }}>{ts}</span>
                    <span style={{
                      fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
                      padding: "2px 6px", borderRadius: 2, flexShrink: 0,
                      background: ok === true ? "rgba(59,130,246,0.12)" : ok === false ? "rgba(239,68,68,0.1)" : "rgba(255,255,255,0.06)",
                      color: ok === true ? "#93C5FD" : ok === false ? "#FCA5A5" : "rgba(255,255,255,0.4)",
                    }}>
                      {type}
                    </span>
                    <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", lineHeight: 1.6, fontWeight: 300 }}>{msg}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── COVERAGE ─────────────────────────────────────────────────────────── */}
      <section style={{ background: "#0D0D14", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, marginBottom: 72 }}>
            <div data-r>
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", display: "block", marginBottom: 24 }}>
                Global Coverage
              </span>
              <h2 style={{ fontFamily: serif, fontSize: "clamp(32px, 3.2vw, 46px)", fontWeight: 400, lineHeight: 1.12, color: "white", letterSpacing: "-0.01em" }}>
                Built for enterprise<br /><em style={{ fontStyle: "italic", color: "rgba(96,165,250,0.9)" }}>at global scale.</em>
              </h2>
            </div>
            <p style={{ fontSize: 21, lineHeight: 1.6, color: "rgba(255,255,255,0.45)", fontWeight: 300, alignSelf: "end", letterSpacing: "-0.01em" }} data-r data-delay="80">
              Financial crime, data protection, governance, and risk — across the world's most significant jurisdictions. Expanding continuously.
            </p>
          </div>

          {/* Jurisdiction grid — no emojis, clean text */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 2 }} data-r data-delay="120">
            {[
              { code: "UK",  name: "United Kingdom",  status: "live"      },
              { code: "US",  name: "United States",   status: "live"      },
              { code: "EU",  name: "European Union",  status: "live"      },
              { code: "SG",  name: "Singapore",       status: "live"      },
              { code: "AE",  name: "UAE",             status: "live"      },
              { code: "AU",  name: "Australia",       status: "live"      },
              { code: "HK",  name: "Hong Kong",       status: "expanding" },
              { code: "CA",  name: "Canada",          status: "expanding" },
              { code: "IN",  name: "India",           status: "expanding" },
              { code: "JP",  name: "Japan",           status: "expanding" },
              { code: "CH",  name: "Switzerland",     status: "expanding" },
              { code: "ZA",  name: "South Africa",    status: "expanding" },
            ].map(({ code, name, status }) => (
              <div key={code} className="dark-card" style={{ background: "rgba(255,255,255,0.03)", padding: "20px" }}>
                <div style={{ fontFamily: "monospace", fontSize: 20, fontWeight: 700, color: status === "live" ? "rgba(59,130,246,0.9)" : "rgba(255,255,255,0.2)", letterSpacing: "0.04em", marginBottom: 10 }}>
                  {code}
                </div>
                <div style={{ fontSize: 12, color: "rgba(255,255,255,0.45)", marginBottom: 8, fontWeight: 400 }}>{name}</div>
                <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: status === "live" ? "rgba(59,130,246,0.7)" : "rgba(255,255,255,0.2)" }}>
                  {status === "live" ? "● Active" : "○ Expanding"}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DOMAINS ──────────────────────────────────────────────────────────── */}
      <section style={{ background: "#F9F9F7", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>

          <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 80, marginBottom: 64 }} data-r>
            <div style={{ paddingTop: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#888", display: "block" }}>
                Coverage
              </span>
            </div>
            <h2 style={{ fontFamily: serif, fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 400, lineHeight: 1.12, color: "#0A0A0F", letterSpacing: "-0.01em" }}>
              Every compliance domain.<br />One platform.
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 2 }} data-r data-delay="80">
            {[
              { t: "AML / KYC / KYB",              d: "Anti-money laundering and customer due diligence." },
              { t: "Sanctions & Screening",          d: "Real-time screening with full audit trail." },
              { t: "Fraud & Transaction Monitoring", d: "Behavioural and pattern-based fraud controls." },
              { t: "Governance & Vendor Risk",       d: "Third-party risk and governance frameworks." },
              { t: "Licensing & Filings",            d: "Regulatory licence and filing obligation management." },
              { t: "Privacy & Data Protection",      d: "GDPR, CCPA, PDPA compliance controls." },
              { t: "Remediation Tracking",           d: "End-to-end workflows with blocking flags." },
              { t: "Regulatory Monitoring",          d: "Continuous alert stream, global sources." },
              { t: "Reporting & Exports",            d: "Structured, regulator-ready report packages." },
              { t: "Tax & Finance Audit",            d: "Financial controls and audit readiness." },
            ].map(({ t, d }) => (
              <div key={t} className="light-card" style={{ borderRadius: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#0A0A0F", marginBottom: 8, letterSpacing: "-0.01em", lineHeight: 1.35 }}>{t}</div>
                <div style={{ fontSize: 12, color: "#888", lineHeight: 1.65, fontWeight: 300 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── REAL ESTATE ──────────────────────────────────────────────────────── */}
      <section style={{ background: "white", padding: "140px 40px", borderTop: "1px solid #EAEAE6", borderBottom: "1px solid #EAEAE6" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 100 }}>

            <div data-r>
              <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#888", display: "block", marginBottom: 24 }}>
                Industry · Real Estate
              </span>
              <h2 style={{ fontFamily: serif, fontSize: "clamp(28px, 3vw, 42px)", fontWeight: 400, lineHeight: 1.15, color: "#0A0A0F", letterSpacing: "-0.01em", marginBottom: 28 }}>
                End-to-end compliance for real estate operations.
              </h2>
              <p style={{ fontSize: 21, lineHeight: 1.6, color: "#444", fontWeight: 300, letterSpacing: "-0.01em" }}>
                AML, KYC, sanctions, and source of funds — mapped directly to controls and evidence workflows. Outputs that withstand real regulatory scrutiny.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column" }} data-r data-delay="80">
              {[
                { t: "Beneficial Ownership",     d: "Structured verification of entity ownership chains." },
                { t: "Source of Funds Review",   d: "Evidence-grounded fund origin scoring against controls." },
                { t: "Sanctions Screening",      d: "Real-time screening across global sanctions lists." },
                { t: "AML Controls Assessment",  d: "Deterministic AML auditing at every transaction level." },
                { t: "Data Protection",          d: "GDPR, CCPA, and local PII obligations — mapped." },
                { t: "Vendor Risk",              d: "Third-party risk across agents, counsel, and contractors." },
              ].map(({ t, d }, i) => (
                <div key={t} style={{ padding: "22px 0", borderBottom: "1px solid #EAEAE6", display: "grid", gridTemplateColumns: "180px 1fr", gap: 24 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#0A0A0F" }}>{t}</div>
                  <div style={{ fontSize: 13, color: "#888", lineHeight: 1.65, fontWeight: 300 }}>{d}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── METRICS ──────────────────────────────────────────────────────────── */}
      <section style={{ background: "#0A0A0F", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 60, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 80 }}>
            <BigStat value="12+" label="Jurisdictions Modelled" note="Live regulatory coverage" />
            <BigStat value="40+" label="Regulatory Regimes"    note="Mapped to control libraries" />
            <BigStat value="300+" label="Compliance Controls"  note="Across all domains" />
            <BigStat value="8"   label="Workflow Stages"       note="Intake through export" />
          </div>
        </div>
      </section>

      {/* ── ENTERPRISE ───────────────────────────────────────────────────────── */}
      <section style={{ background: "#F9F9F7", padding: "140px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>

          <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 80, marginBottom: 80 }} data-r>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "#888", paddingTop: 6 }}>
              Enterprise Readiness
            </span>
            <h2 style={{ fontFamily: serif, fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 400, lineHeight: 1.12, color: "#0A0A0F", letterSpacing: "-0.01em" }}>
              Built for serious organisations.
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2 }} data-r data-delay="80">
            {[
              { n: "01", t: "Tenant Isolation",          d: "Complete data isolation at every layer. No leakage across organisational boundaries." },
              { n: "02", t: "Immutable Audit Trail",      d: "Every action logged and preserved by design. Regulator-ready from day one." },
              { n: "03", t: "Human-Reviewable Outputs",   d: "Every finding cites its exact evidence and control. No opaque AI decisions." },
              { n: "04", t: "Role-Based Workflows",       d: "Owner, reviewer, and auditor roles across every workflow stage." },
              { n: "05", t: "Evidence Chain of Custody",  d: "Full provenance tracking from upload through export. Traceable at every stage." },
              { n: "06", t: "Global Regulatory Mapping",  d: "Frameworks mapped across all major jurisdictions. Expansion-ready architecture." },
            ].map(({ n, t, d }) => (
              <div key={n} className="light-card" style={{ borderRadius: 0, borderLeft: "3px solid transparent", transition: "border-color 0.25s, box-shadow 0.25s" }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderLeftColor = "#1E40AF"; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderLeftColor = "transparent"; }}>
                <div style={{ fontFamily: "monospace", fontSize: 10, fontWeight: 700, color: "#AAA", letterSpacing: "0.1em", marginBottom: 12 }}>{n}</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: "#0A0A0F", marginBottom: 10, letterSpacing: "-0.01em" }}>{t}</div>
                <div style={{ fontSize: 14, color: "#666", lineHeight: 1.7, fontWeight: 300 }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ────────────────────────────────────────────────────────── */}
      <section id="demo" style={{ position: "relative", background: "#0A0A0F", padding: "180px 40px", overflow: "hidden" }}>
        <OrbitalCanvas />
        <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 70% 70% at 50% 50%, rgba(10,10,15,0.85) 0%, rgba(10,10,15,0.6) 50%, transparent 100%)", pointerEvents: "none" }} />

        <div style={{ position: "relative", maxWidth: 720, margin: "0 auto", textAlign: "center" }} data-r>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 36 }}>
            <span style={{ width: 32, height: 1, background: "rgba(59,130,246,0.5)" }} />
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.14em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)" }}>
              Get Started
            </span>
            <span style={{ width: 32, height: 1, background: "rgba(59,130,246,0.5)" }} />
          </div>

          <h2 style={{ fontFamily: serif, fontSize: "clamp(40px, 5vw, 68px)", fontWeight: 400, lineHeight: 1.08, color: "white", letterSpacing: "-0.01em", margin: "0 0 20px" }}>
            See Tenet<br /><em style={{ fontStyle: "italic", color: "rgba(96,165,250,0.9)" }}>in action.</em>
          </h2>

          <p style={{ fontSize: 21, color: "rgba(255,255,255,0.4)", margin: "0 0 48px", fontWeight: 300, lineHeight: 1.55, letterSpacing: "-0.01em" }}>
            See what enterprise compliance intelligence actually looks like.
          </p>

          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <a href="#" className="btn-primary">
              Request a Demo
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </a>
            <Link href="/dashboard" className="btn-ghost">Sign In to Platform</Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ───────────────────────────────────────────────────────────── */}
      <footer style={{ background: "#06060A", borderTop: "1px solid rgba(255,255,255,0.05)", padding: "72px 40px 40px" }}>
        <div style={{ maxWidth: 1280, margin: "0 auto" }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr", gap: 48, marginBottom: 60 }}>

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
                  <path d="M10 2L18 7V13L10 18L2 13V7L10 2Z" stroke="rgba(59,130,246,0.7)" strokeWidth="1.2" fill="rgba(59,130,246,0.1)" />
                  <circle cx="10" cy="10" r="2.5" fill="rgba(59,130,246,0.8)" />
                </svg>
                <span style={{ fontFamily: sans, color: "white", fontWeight: 600, fontSize: 13, letterSpacing: "0.08em", textTransform: "uppercase" }}>Tenet</span>
              </div>
              <p style={{ fontSize: 13, color: "rgba(255,255,255,0.25)", lineHeight: 1.7, maxWidth: 220, fontWeight: 300 }}>
                The compliance intelligence platform for modern enterprises.
              </p>
            </div>

            {[
              { col: "Platform",  links: ["Audit Engine", "Evidence Review", "Remediation", "Monitoring", "Reporting"] },
              { col: "Solutions", links: ["Financial Services", "Real Estate", "Healthcare", "Technology", "Insurance"] },
              { col: "Company",   links: ["About", "Careers", "Security", "Blog", "Contact"] },
              { col: "Legal",     links: ["Privacy Policy", "Terms of Service", "Cookie Policy", "DPA"] },
            ].map(({ col, links }) => (
              <div key={col}>
                <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.25)", marginBottom: 20 }}>
                  {col}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {links.map((l) => (
                    <a key={l} href="#" style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", textDecoration: "none", fontWeight: 300, transition: "color 0.2s" }}
                      onMouseEnter={e => (e.target as HTMLElement).style.color = "rgba(255,255,255,0.7)"}
                      onMouseLeave={e => (e.target as HTMLElement).style.color = "rgba(255,255,255,0.35)"}>
                      {l}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: 28, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.18)", fontWeight: 300 }}>© 2026 Tenet. All rights reserved.</span>
            <span style={{ fontSize: 12, color: "rgba(255,255,255,0.18)", fontWeight: 300 }}>Compliance intelligence for the modern enterprise.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
