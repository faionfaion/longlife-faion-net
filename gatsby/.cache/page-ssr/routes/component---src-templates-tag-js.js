"use strict";
exports.id = 502;
exports.ids = [502];
exports.modules = {

/***/ 1804:
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   Head: () => (/* binding */ Head),
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(1809);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var gatsby__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(123);
/* harmony import */ var _components_layout__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(3895);
const TagTemplate=({data,pageContext})=>{const{tag}=pageContext;const articles=data.allMarkdownRemark.nodes;return/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement(_components_layout__WEBPACK_IMPORTED_MODULE_2__/* ["default"] */ .A,null,/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("h1",null,"#",tag),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("p",null,articles.length," \u0441\u0442\u0430\u0442\u0435\u0439"),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("div",{className:"articles-grid"},articles.map(article=>/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("article",{key:article.frontmatter.slug,className:"article-card"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement(gatsby__WEBPACK_IMPORTED_MODULE_1__.Link,{to:`/${article.frontmatter.slug}/`},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("h3",null,article.frontmatter.title),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("p",{className:"description"},article.frontmatter.description),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("time",null,article.frontmatter.date))))));};const query="444913933";/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (TagTemplate);const Head=({pageContext})=>/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement((react__WEBPACK_IMPORTED_MODULE_0___default().Fragment),null,/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("title",null,"#",pageContext.tag," \u2014 \u041F\u0430\u0448\u0442\u0435\u043B\u044C\u043A\u0430"),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("html",{lang:"uk"}));

/***/ }),

/***/ 3895:
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   A: () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(1809);
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var gatsby__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(123);
const Layout=({children})=>/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("div",{className:"site"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("header",{className:"site-header"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("div",{className:"container"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement(gatsby__WEBPACK_IMPORTED_MODULE_1__.Link,{to:"/",className:"site-logo"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("span",{className:"logo-icon"},"\uD83C\uDF3F"),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("span",{className:"logo-text"},"LongLife")))),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("main",{className:"container"},children),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("footer",{className:"site-footer"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("div",{className:"container"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("p",{className:"footer-brand"},"LongLife Media"),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("p",{className:"footer-desc"},"\u0414\u043E\u043A\u0430\u0437\u043E\u0432\u0430 \u043C\u0435\u0434\u0438\u0446\u0438\u043D\u0430, \u0434\u043E\u0441\u043B\u0456\u0434\u0436\u0435\u043D\u043D\u044F, \u0433\u0430\u0439\u0434\u0438 \u0442\u0430 \u043B\u0430\u0439\u0444\u0445\u0430\u043A\u0438",/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("br",null),"\u0434\u043B\u044F \u0437\u0434\u043E\u0440\u043E\u0432\u043E\u0433\u043E \u0442\u0430 \u0434\u043E\u0432\u0433\u043E\u0433\u043E \u0436\u0438\u0442\u0442\u044F."),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("a",{href:"https://t.me/long_life_media",target:"_blank",rel:"noopener noreferrer",className:"footer-tg"},"\u041F\u0456\u0434\u043F\u0438\u0441\u0430\u0442\u0438\u0441\u044F \u0432 Telegram"),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("div",{className:"footer-links"},/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("a",{href:"/sitemap-index.xml"},"Sitemap")),/*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0___default().createElement("p",{className:"footer-copyright"},"\xA9 ",new Date().getFullYear()," LongLife Media"))));/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (Layout);

/***/ })

};
;
//# sourceMappingURL=component---src-templates-tag-js.js.map