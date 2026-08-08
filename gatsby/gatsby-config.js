module.exports = {
  siteMetadata: {
    title: "Віта Зеленко — про здоров’я з поглядом на дослідження",
    description: "Науковиця в галузі здоров’я читає дослідження і пише, що з них насправді випливає. Один допис на день, українською.",
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
