const path = require("path");

exports.createPages = async ({ graphql, actions }) => {
  const { createPage } = actions;

  const result = await graphql(`
    {
      allMarkdownRemark(sort: { frontmatter: { date: DESC } }) {
        nodes {
          frontmatter {
            slug
            title
            date
            type
            tags
            author
            description
            source_urls
            source_names
          }
          html
          wordCount {
            words
          }
        }
      }
    }
  `);

  if (result.errors) {
    throw result.errors;
  }

  const articles = result.data.allMarkdownRemark.nodes;

  // Create article pages
  articles.forEach((article, index) => {
    const slug = article.frontmatter.slug;
    const prev = index < articles.length - 1 ? articles[index + 1] : null;
    const next = index > 0 ? articles[index - 1] : null;

    createPage({
      path: `/${slug}/`,
      component: path.resolve("./src/templates/article.js"),
      context: {
        slug,
        prev: prev ? { slug: prev.frontmatter.slug, title: prev.frontmatter.title } : null,
        next: next ? { slug: next.frontmatter.slug, title: next.frontmatter.title } : null,
      },
    });
  });

  // Create tag pages
  const tagSet = new Set();
  articles.forEach((article) => {
    (article.frontmatter.tags || []).forEach((tag) => tagSet.add(tag));
  });

  tagSet.forEach((tag) => {
    createPage({
      path: `/tag/${encodeURIComponent(tag)}/`,
      component: path.resolve("./src/templates/tag.js"),
      context: { tag },
    });
  });
};
