import React from "react";
import { Link } from "gatsby";
import "./layout.css";

const Layout = ({ children }) => (
  <div className="site">
    <header className="site-header">
      <div className="container">
        <Link to="/" className="site-logo">
          <span className="logo-icon">🌿</span>
          <span className="logo-text">LongLife</span>
        </Link>
      </div>
    </header>
    <main className="container">{children}</main>
    <footer className="site-footer">
      <div className="container">
        <p className="footer-brand">LongLife Media</p>
        <p className="footer-desc">
          Доказова медицина, дослідження, гайди та лайфхаки
          <br />
          для здорового та довгого життя.
        </p>
        <a
          href="https://t.me/long_life_media"
          target="_blank"
          rel="noopener noreferrer"
          className="footer-tg"
        >
          Підписатися в Telegram
        </a>
        <div className="footer-links">
          <a href="/sitemap-index.xml">Sitemap</a>
        </div>
        <p className="footer-copyright">
          &copy; {new Date().getFullYear()} LongLife Media
        </p>
      </div>
    </footer>
  </div>
);

export default Layout;
