import React from "react";
import { graphql, Link } from "gatsby";
import Layout from "../components/layout";

const TagTemplate = ({ data, pageContext }) => {
  const { tag } = pageContext;
  const articles = data.allMarkdownRemark.nodes;

  return (
    <Layout>
      <h1>#{tag}</h1>
      <p>{articles.length} статей</p>
      <div className="articles-grid">
        {articles.map((article) => (
          <article key={article.frontmatter.slug} className="article-card">
            <Link to={`/${article.frontmatter.slug}/`}>
              <h3>{article.frontmatter.title}</h3>
              <p className="description">{article.frontmatter.description}</p>
              <time>{article.frontmatter.date}</time>
            </Link>
          </article>
        ))}
      </div>
    </Layout>
  );
};

export const query = graphql`
  query ($tag: String!) {
    allMarkdownRemark(
      filter: { frontmatter: { tags: { in: [$tag] } } }
      sort: { frontmatter: { date: DESC } }
    ) {
      nodes {
        frontmatter {
          slug
          title
          date
          description
        }
      }
    }
  }
`;

export default TagTemplate;

export const Head = ({ pageContext }) => (
  <>
    <title>#{pageContext.tag} — Паштелька</title>
    <html lang="uk" />
  </>
);
