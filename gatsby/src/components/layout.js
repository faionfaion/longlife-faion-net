import React from "react";
import { Link } from "gatsby";
import "./layout.css";

// A blog, not a publication: the header carries her name and what she does, not a
// masthead, and the footer signs off as a person rather than as an organisation.
const Layout = ({ children }) => (
  <div className="site">
    <header className="site-header">
      <div className="container">
        <Link to="/" className="site-logo">
          <span className="logo-text">Віта Зеленко</span>
          <span className="logo-tagline">
            про здоров’я, з поглядом на дослідження
          </span>
        </Link>
        <nav className="site-nav">
          <Link to="/pidpyska/">Підписка</Link>
          <Link to="/pro-mene/">Про мене</Link>
          <a
            href="https://t.me/long_life_media"
            target="_blank"
            rel="noopener noreferrer"
          >
            Telegram
          </a>
        </nav>
      </div>
    </header>
    <main className="container">{children}</main>
    <footer className="site-footer">
      <div className="container">
        <p className="footer-brand">Віта Зеленко</p>
        <p className="footer-desc">
          Я науковиця в галузі здоров’я. Читаю дослідження й пишу тут про те,
          <br />
          що з них насправді випливає, і де я сама ще не певна.
        </p>
        <a
          href="https://t.me/long_life_media"
          target="_blank"
          rel="noopener noreferrer"
          className="footer-tg"
        >
          Читати в Telegram
        </a>
        <div className="footer-links">
          <Link to="/pidpyska/">Підписка</Link>
          <Link to="/pro-mene/">Про мене</Link>
          <Link to="/umovy-vykorystannya/">Умови використання</Link>
          <a href="/rss.xml">RSS</a>
          <a href="/sitemap-index.xml">Sitemap</a>
        </div>
        <p className="footer-copyright">
          &copy; {new Date().getFullYear()} Віта Зеленко
        </p>
      </div>
    </footer>
  </div>
);

export default Layout;
