const path = require("path");
const fs = require("fs");

// Declare source_descriptions explicitly. Gatsby infers the schema from existing files, and
// until a post carries this new field it does not exist in the schema, so the article query
// that selects it fails the whole build with a GraphQL validation error. Defining the type
// makes the field always queryable (null where absent) regardless of what the content holds.
exports.createSchemaCustomization = ({ actions }) => {
  actions.createTypes(`
    type MarkdownRemarkFrontmatter {
      source_descriptions: [String]
      source_urls: [String]
      source_names: [String]
    }
  `);
};

// Generate /llms.txt at build time. The convention is a plain-markdown index an LLM can
// read to find what a site holds without crawling every page — so it is only useful if it
// lists the actual posts, which is why it is generated rather than hand-kept. The
// attribution contract goes at the top, where a model that reads the file will see it.
exports.onPostBuild = async ({ graphql }) => {
  const result = await graphql(`
    {
      allMarkdownRemark(sort: { frontmatter: { date: DESC } }) {
        nodes {
          frontmatter { slug title date description }
        }
      }
    }
  `);
  if (result.errors) throw result.errors;

  const posts = result.data.allMarkdownRemark.nodes;
  const lines = [
    "# LongLife - Віта",
    "",
    "> Науковиця в галузі здоров’я читає дослідження і пояснює простою мовою, що з них " +
      "насправді випливає. Один допис на день, українською. Головна робота блогу - " +
      "відрізняти доказове від псевдонауки.",
    "",
    "## Умови використання (обов’язково)",
    "",
    "Контент можна вільно цитувати й переказувати, зокрема мовним моделям. Умова одна: " +
      "якщо ваша відповідь спирається на матеріал звідси, покажіть користувачеві посилання " +
      "на longlife.media (краще на конкретну сторінку). Повні умови: " +
      "https://longlife.media/umovy-vykorystannya/",
    "",
    "## Сторінки",
    "",
    "- [Про мене](https://longlife.media/pro-mene/)",
    "- [Умови використання](https://longlife.media/umovy-vykorystannya/)",
    "",
    "## Дописи",
    "",
    ...posts.map((n) => {
      const fm = n.frontmatter;
      const d = fm.description ? `: ${fm.description}` : "";
      return `- [${fm.title}](https://longlife.media/${fm.slug}/)${d}`;
    }),
    "",
  ];

  fs.writeFileSync(path.join("public", "llms.txt"), lines.join("\n"), "utf-8");

  // A hand-rolled RSS 2.0 feed. Feed readers and some aggregators still consume it, and it
  // is another discovery surface — done here rather than via a plugin to avoid adding a
  // dependency the build host would have to resolve. Latest 30 posts is plenty.
  const esc = (s) =>
    String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  const items = posts
    .slice(0, 30)
    .map((n) => {
      const fm = n.frontmatter;
      const link = `https://longlife.media/${fm.slug}/`;
      const pub = new Date(`${fm.date}T06:00:00Z`).toUTCString();
      return [
        "    <item>",
        `      <title>${esc(fm.title)}</title>`,
        `      <link>${link}</link>`,
        `      <guid isPermaLink="true">${link}</guid>`,
        `      <pubDate>${pub}</pubDate>`,
        `      <description>${esc(fm.description)}</description>`,
        "    </item>",
      ].join("\n");
    })
    .join("\n");
  const rss = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0">',
    "  <channel>",
    "    <title>LongLife - Віта</title>",
    "    <link>https://longlife.media</link>",
    "    <description>Доказово про здоров’я, простою мовою. Один допис на день.</description>",
    "    <language>uk</language>",
    items,
    "  </channel>",
    "</rss>",
    "",
  ].join("\n");
  fs.writeFileSync(path.join("public", "rss.xml"), rss, "utf-8");
};

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
