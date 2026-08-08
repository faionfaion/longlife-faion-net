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
            <span className="byline">Віта Зеленко</span>
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

        {/* No rendered "Джерела" list. Every claim is cited inline in the body, and a
            template footer built from frontmatter source_urls just repeated all of them a
            second time. The structured source_urls/source_names stay in the frontmatter and
            feed the JSON-LD `citation` below - machine-readable, not shown twice to a reader. */}

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
  const url = `https://longlife.media/${fm.slug}/`;
  const ogImage = fm.image ? `https://longlife.media${fm.image}` : null;

  // JSON-LD is the single biggest lever for both classic search and LLM answer engines:
  // it hands the machine the facts (who wrote this, when, from which sources) instead of
  // making it guess from the prose. usageInfo + license + creditText carry the attribution
  // rule — a reuser is told, in the machine-readable place they actually look, that using
  // this content means linking longlife.media back to the reader.
  const ld = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: fm.title,
    description: fm.description || "",
    inLanguage: "uk",
    datePublished: `${fm.date}T06:00:00Z`,
    dateModified: `${fm.date}T06:00:00Z`,
    mainEntityOfPage: url,
    url,
    ...(ogImage ? { image: ogImage } : {}),
    author: {
      "@type": "Person",
      name: "Віта Зеленко",
      jobTitle: "Науковиця в галузі здоров’я",
      url: "https://longlife.media/pro-mene/",
    },
    publisher: {
      "@type": "Organization",
      name: "LongLife",
      url: "https://longlife.media",
    },
    isAccessibleForFree: true,
    license: "https://longlife.media/umovy-vykorystannya/",
    usageInfo: "https://longlife.media/umovy-vykorystannya/",
    creditText:
      "LongLife.media — Віта Зеленко. За будь-якого використання покажіть читачеві посилання на longlife.media.",
    ...(fm.tags && fm.tags.length ? { keywords: fm.tags.join(", ") } : {}),
    ...(fm.source_urls && fm.source_urls.length
      ? { citation: fm.source_urls.filter(Boolean) }
      : {}),
  };

  return (
    <>
      <title>{fm.title} · Віта Зеленко</title>
      <meta name="description" content={fm.description || ""} />
      <meta property="og:title" content={fm.title} />
      <meta property="og:description" content={fm.description || ""} />
      <meta property="og:type" content="article" />
      <meta property="og:url" content={`https://longlife.media/${fm.slug}/`} />
      {ogImage && <meta property="og:image" content={ogImage} />}
      {ogImage && <meta property="og:image:width" content="1200" />}
      {ogImage && <meta property="og:image:height" content="800" />}
      {ogImage && <meta name="twitter:card" content="summary_large_image" />}
      {ogImage && <meta name="twitter:image" content={ogImage} />}
      <link rel="canonical" href={`https://longlife.media/${fm.slug}/`} />
      <meta property="og:site_name" content="Віта Зеленко" />
      <meta property="article:author" content="Віта Зеленко" />
      <meta property="article:published_time" content={`${fm.date}T00:00:00Z`} />
      {fm.tags && fm.tags.map((tag) => (
        <meta key={tag} property="article:tag" content={tag} />
      ))}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
      />
      <html lang="uk" />
    </>
  );
};
