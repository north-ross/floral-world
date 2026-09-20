import MarkdownItFootnote from "markdown-it-footnote";
// See https://observablehq.com/framework/config for documentation.
export default {
  // The app’s title; used in the sidebar and webpage titles.
  title: "Floral World",

  // The pages and sections in the sidebar. If you don’t specify this option,
  // all pages will be listed in alphabetical order. Listing pages explicitly
  // lets you organize them into sections and have unlisted pages.
  // pages: [
  //   {
  //     name: "Examples",
  //     pages: [
  //       {name: "Dashboard", path: "/example-dashboard"},
  //       {name: "Report", path: "/example-report"}
  //     ]
  //   }
  // ],

  // Content to add to the head of the page, e.g. for a favicon:
  head: '<link rel="icon" href="observable.png" type="image/png" sizes="32x32">',

  // The path to the source root.
  root: "src",
  base: "/floral-world",

  markdownIt: (md) => md.use(MarkdownItFootnote),

  // Some additional configuration options and their defaults:
  theme: ["parchment"], //, "coffee"],
  // header: "", // what to show in the header (HTML)
  footer: "Map data adapted from <a href=\"https://www.tdwg.org/standards/wgsrpd/\">World\
Geographic System for Recording Plant Distributions</a>, with species distributions from \
the <a href=\"https://powo.science.kew.org/about-wcvp\">World Checklist of Vascular Plants</a> (updated weekly). \
English common names are from the <a href=\"https://forum.inaturalist.org/t/list-of-sources-for-common-names-wiki/10249\">iNaturalist Community</a>, downloaded <a href=\"https://www.inaturalist.ca/pages/developers\">here</a>. \
Additional data and images from <a href=\"https://www.wikidata.org\">Wikidata</a>. \
Built with Observable. Some AI was used to assist develpment. \
<a href=\"https://github.com/north-ross/floral-world#use-of-ai\">Read more</a>", // what to show in the footer (HTML)
  // sidebar: true, // whether to show the sidebar
  // toc: true, // whether to show the table of contents
  // pager: true, // whether to show previous & next links in the footer
  // output: "dist", // path to the output root for build
  // search: true, // activate search
  // linkify: true, // convert URLs in Markdown to links
  // typographer: false, // smart quotes and other typographic improvements
  // preserveExtension: false, // drop .html from URLs
  // preserveIndex: false, // drop /index from URLs
};
