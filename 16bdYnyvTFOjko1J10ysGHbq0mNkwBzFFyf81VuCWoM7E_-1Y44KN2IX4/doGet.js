/**
 * Web App entry point.
 * Routes requests based on the path info.
 * @param {Object} e The event parameter.
 * @return {HtmlOutput|ContentOutput} The HTML output or Content service output.
 */
function doGet(e) {
  const path = e.pathInfo;

  if (path === 'json') {
    return getJsonResponse();
  } else if (path === 'readme') {
    return HtmlService.createTemplateFromFile('readme').evaluate()
        .setTitle('仕様書 - GAS Project Finder');
  } else if (path === 'test') {
    return HtmlService.createTemplateFromFile('test').evaluate()
        .setTitle('APIテスト - GAS Project Finder');
  } else {
    return HtmlService.createTemplateFromFile('index')
        .evaluate()
        .setTitle('Google Apps Script プロジェクト検索')
        .addMetaTag('viewport', 'width=device-width, initial-scale=1');
  }
}
