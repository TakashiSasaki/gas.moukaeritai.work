function doGet(e) {
  let pathInfo = e.pathInfo;
  let pageToLoad = "index"; // Default page

  if (pathInfo !== undefined && pathInfo !== "" && pathInfo !== "/") {
    pageToLoad = pathInfo.substring(1); // Remove leading slash
  }

  let baseUrl = ScriptApp.getService().getUrl();
  if (baseUrl.endsWith('/')) {
    baseUrl = baseUrl.slice(0, -1);
  }

  let template;
  let title;

  if (pageToLoad === 'index') {
    template = HtmlService.createTemplateFromFile('index');
    title = 'Spreadsheet Viewer - Display';
  } else if (pageToLoad === 'settings') {
    template = HtmlService.createTemplateFromFile('settings');
    title = 'Spreadsheet Viewer - Settings';
  } else if (pageToLoad === 'readme') {
    template = HtmlService.createTemplateFromFile('readme');
    title = 'Spreadsheet Viewer - Readme';
  } else {
    // Handle unknown paths
    return HtmlService.createHtmlOutput("Page not found: " + (e.pathInfo ? e.pathInfo : "root"))
        .setTitle('Error - Page Not Found');
  }

  template.baseUrl = baseUrl;
  template.indexUrl = baseUrl; // Explicitly set indexUrl which is same as baseUrl
  template.settingsUrl = baseUrl + '/settings';
  template.readmeUrl = baseUrl + '/readme';
  template.currentPage = pageToLoad; // Pass 'index', 'settings', or 'readme'

  return template.evaluate().setTitle(title);
}
