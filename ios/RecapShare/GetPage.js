// Runs inside the Safari page when the user taps Share → Recap.
// Hands the page URL, title and rendered HTML to the share extension
// (arrives as NSExtensionJavaScriptPreprocessingResultsKey).
var GetPage = function () {};

GetPage.prototype = {
  run: function (args) {
    args.completionFunction({
      url: document.URL,
      title: document.title,
      html: document.documentElement.outerHTML,
    });
  },
};

var ExtensionPreprocessingJS = new GetPage();
