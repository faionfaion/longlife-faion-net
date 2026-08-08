import React, { useState } from "react";
import { Link } from "gatsby";
import "./layout.css";

// The header is just the masthead now. Everything to do - subscribe, about, Telegram -
// lives in the footer, where the email form sits inline so a reader can sign up from the
// bottom of any post without a detour to a separate page.

// Compact footer sign-up. Double opt-in through the same /api/subscribe as the full page;
// this one defaults to the weekly digest, and points to /pidpyska for the finer choices.
function FooterSubscribe() {
  const [email, setEmail] = useState("");
  const [hp, setHp] = useState("");
  const [state, setState] = useState("idle");

  const submit = async (e) => {
    e.preventDefault();
    setState("sending");
    try {
      const r = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, hp, weekly: true }),
      });
      setState(r.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  };

  if (state === "sent") {
    return (
      <p className="footer-sub-done">
        Готово. Я надіслала лист на {email} - відкрий посилання в ньому, щоб
        підтвердити.
      </p>
    );
  }

  return (
    <form className="footer-sub" onSubmit={submit}>
      <label className="footer-sub-label" htmlFor="footer-email">
        Доказово про здоров’я, простою мовою - на пошту
      </label>
      <div className="footer-sub-row">
        <input
          id="footer-email"
          type="email"
          required
          placeholder="твоя пошта"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="text"
          name="website"
          tabIndex="-1"
          autoComplete="off"
          aria-hidden="true"
          value={hp}
          onChange={(e) => setHp(e.target.value)}
          style={{ position: "absolute", left: "-9999px" }}
        />
        <button type="submit" disabled={state === "sending"}>
          {state === "sending" ? "…" : "Підписатися"}
        </button>
      </div>
      {state === "error" && (
        <p className="footer-sub-err">Не вдалося. Спробуй ще раз згодом.</p>
      )}
      <p className="footer-sub-fine">
        Тижневий дайджест. <Link to="/pidpyska/">Обрати, що надсилати</Link>.
        Відписатися можна будь-коли.
      </p>
    </form>
  );
}

const Layout = ({ children }) => (
  <div className="site">
    <header className="site-header">
      <div className="container">
        <Link to="/" className="site-logo">
          <span className="logo-text">Віта</span>
          <span className="logo-tagline">
            про здоров’я, з поглядом на дослідження
          </span>
        </Link>
      </div>
    </header>
    <main className="container">{children}</main>
    <footer className="site-footer">
      <div className="container">
        <p className="footer-brand">Віта</p>
        <p className="footer-desc">
          Я науковиця в галузі здоров’я. Читаю дослідження й пишу тут про те,
          що з них насправді випливає, і де я сама ще не певна.
        </p>

        <FooterSubscribe />

        <nav className="footer-links">
          <Link to="/pidpyska/">Підписка</Link>
          <Link to="/pro-mene/">Про мене</Link>
          <a
            href="https://t.me/long_life_media"
            target="_blank"
            rel="noopener noreferrer"
          >
            Telegram
          </a>
          <Link to="/umovy-vykorystannya/">Умови використання</Link>
          <a href="/rss.xml">RSS</a>
          <a href="/sitemap-index.xml">Sitemap</a>
        </nav>

        <p className="footer-copyright">
          &copy; {new Date().getFullYear()} Віта
        </p>
      </div>
    </footer>
  </div>
);

export default Layout;
