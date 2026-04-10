module.exports = {
  siteMetadata: {
    title: "LongLife — Здоровий спосіб життя",
    description: "Доказова медицина, дослідження, гайди, лайфхаки для здорового та довгого життя. Українською.",
    siteUrl: "https://longlife.faion.net",
    author: "Віта Зеленко",
  },
  plugins: [
    {
      resolve: "gatsby-source-filesystem",
      options: {
        name: "content",
        path: `${__dirname}/../content`,
      },
    },
    {
      resolve: "gatsby-source-filesystem",
      options: {
        name: "images",
        path: `${__dirname}/static/images`,
      },
    },
    "gatsby-transformer-remark",
    "gatsby-plugin-sharp",
    "gatsby-transformer-sharp",
    "gatsby-plugin-sitemap",
  ],
};
