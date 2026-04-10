import React from "react";
import { graphql, Link } from "gatsby";
import Layout from "../components/layout";

const IndexPage = ({ data }) => {
  const articles = data.allMarkdownRemark.nodes;

  const grouped = {};
  articles.forEach((article) => {
    const date = article.frontmatter.date;
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(article);
  });

  const formatDate = (dateStr) => {
    const d = new Date(dateStr + "T12:00:00");
    return d.toLocaleDateString("uk-UA", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <Layout>
      <div className="hero-section">
        <span className="badge">Здоровий спосіб життя</span>
        <p className="subtitle">
          Доказова медицина, дослідження, гайди та лайфхаки для здорового та довгого життя
        </p>
      </div>

      {Object.entries(grouped).map(([date, posts]) => (
        <div key={date} className="date-group">
          <h2 className="date-header">{formatDate(date)}</h2>
          <div className="articles-grid">
            {posts.map((article) => (
              <article key={article.frontmatter.slug} className="article-card">
                <Link to={`/${article.frontmatter.slug}/`}>
                  {article.frontmatter.image && (
                    <img
                      className="card-image"
                      src={article.frontmatter.image}
                      alt=""
                      loading="lazy"
                    />
                  )}
                  <div className="card-content">
                    <span className={`type-badge type-${article.frontmatter.type}`}>
                      {article.frontmatter.type}
                    </span>
                    <h3>{article.frontmatter.title}</h3>
                    <p className="description">{article.frontmatter.description}</p>
                    <div className="meta">
                      <span>{Math.ceil(article.wordCount.words / 200)} xв</span>
                    </div>
                  </div>
                </Link>
              </article>
            ))}
          </div>
        </div>
      ))}
    </Layout>
  );
};

export const query = graphql`
  {
    allMarkdownRemark(
      sort: { frontmatter: { date: DESC } }
      limit: 60
    ) {
      nodes {
        frontmatter {
          slug
          title
          date
          type
          description
          tags
          image
        }
        wordCount {
          words
        }
      }
    }
  }
`;

export default IndexPage;

export const Head = () => (
  <>
    <title>LongLife — Здоровий спосіб життя</title>
    <meta name="description" content="Доказова медицина, дослідження, гайди та лайфхаки для здорового та довгого життя. Українською." />
    <meta property="og:title" content="LongLife — Здоровий спосіб життя" />
    <meta property="og:description" content="Доказова медицина, дослідження, гайди та лайфхаки для здорового та довгого життя." />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://longlife.faion.net" />
    <meta property="og:site_name" content="LongLife Media" />
    <html lang="uk" />
  </>
);
