
// prefer default export if available
const preferDefault = m => (m && m.default) || m


exports.components = {
  "component---src-pages-index-js": preferDefault(require("/home/faion/longlife-faion-net/gatsby/src/pages/index.js")),
  "component---src-templates-article-js": preferDefault(require("/home/faion/longlife-faion-net/gatsby/src/templates/article.js")),
  "component---src-templates-tag-js": preferDefault(require("/home/faion/longlife-faion-net/gatsby/src/templates/tag.js"))
}

