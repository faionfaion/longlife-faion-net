import React from "react";
import { graphql, Link } from "gatsby";
import Layout from "../components/layout";

const ArticleTemplate = ({ data, pageContext }) => {
  const article = data.markdownRemark;
  const { prev, next } = pageContext;
  const fm = article.frontmatter;

  return (
    <Layout>
      <article className="article-full" data-iv="true">
        <header>
          <div className="article-top">
            <span className={`type-badge type-${fm.type}`}>{fm.type}</span>
            <time dateTime={fm.date}>
              {new Date(fm.date + "T12:00:00").toLocaleDateString("uk-UA", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </time>
          </div>
          <h1>{fm.title}</h1>
          <div className="article-meta">
            <span className="reading-time">
              {Math.ceil(article.wordCount.words / 200)} хв читання
            </span>
          </div>
        </header>

        <div className="article-body">
          {fm.image && (
            <div className="hero-wrap">
              <img src={fm.image} alt={fm.title} loading="eager" />
            </div>
          )}
          <div dangerouslySetInnerHTML={{ __html: article.html }} />
        </div>

        {fm.tags && (
          <div className="article-tags">
            {fm.tags.map((tag) => (
              <Link key={tag} to={`/tag/${encodeURIComponent(tag)}/`} className="tag">
                #{tag}
              </Link>
            ))}
          </div>
        )}

        {fm.source_urls && fm.source_urls.length > 0 && (
          <footer className="sources">
            <h3>Джерела</h3>
            <ul>
              {fm.source_urls.map((url, i) => (
                <li key={i}>
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    {fm.source_names && fm.source_names[i]
                      ? fm.source_names[i]
                      : (() => { try { return new URL(url).hostname; } catch { return url; } })()}
                  </a>
                </li>
              ))}
            </ul>
          </footer>
        )}

        <nav className="article-nav">
          {prev && (
            <Link to={`/${prev.slug}/`} className="nav-prev">
              &larr; {prev.title}
            </Link>
          )}
          {next && (
            <Link to={`/${next.slug}/`} className="nav-next">
              {next.title} &rarr;
            </Link>
          )}
        </nav>
      </article>
    </Layout>
  );
};

export const query = graphql`
  query ($slug: String!) {
    markdownRemark(frontmatter: { slug: { eq: $slug } }) {
      html
      wordCount {
        words
      }
      frontmatter {
        title
        slug
        date
        type
        author
        description
        tags
        source_urls
        source_names
        image
      }
    }
  }
`;

export default ArticleTemplate;

export const Head = ({ data }) => {
  const fm = data.markdownRemark.frontmatter;
  const ogImage = fm.image
    ? `https://pastelka.news${fm.image}`
    : null;
  return (
    <>
      <title>{fm.title} — Паштелька News</title>
      <meta name="description" content={fm.description || ""} />
      <meta property="og:title" content={fm.title} />
      <meta property="og:description" content={fm.description || ""} />
      <meta property="og:type" content="article" />
      <meta property="og:url" content={`https://pastelka.news/${fm.slug}/`} />
      {ogImage && <meta property="og:image" content={ogImage} />}
      {ogImage && <meta property="og:image:width" content="1200" />}
      {ogImage && <meta property="og:image:height" content="800" />}
      {ogImage && <meta name="twitter:card" content="summary_large_image" />}
      {ogImage && <meta name="twitter:image" content={ogImage} />}
      <link rel="canonical" href={`https://pastelka.news/${fm.slug}/`} />
      <meta property="og:site_name" content="Паштелька News" />
      <meta property="article:author" content="Паштелька News" />
      <meta property="article:published_time" content={`${fm.date}T00:00:00Z`} />
      {fm.tags && fm.tags.map((tag) => (
        <meta key={tag} property="article:tag" content={tag} />
      ))}
      <html lang="uk" />
    </>
  );
};
