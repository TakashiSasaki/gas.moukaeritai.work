function doGet(e) {
  return HtmlService.createTemplateFromFile('index')
      .evaluate()
      .setTitle('Spreadsheet Viewer');
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename)
      .getContent();
}

/**
 * Google Driveからスプレッドシートを名前で検索し、UserCacheにキャッシュします。
 * @param {string} nameQuery 検索するスプレッドシート名の一部
 * @returns {Array<Object>} IDと名前を持つスプレッドシートのリスト
 */
function searchSpreadsheetsByName(nameQuery) {
  const cache = CacheService.getUserCache();
  const cacheKey = 'spreadsheet_search_' + nameQuery.toLowerCase();
  const cachedResult = cache.get(cacheKey);

  if (cachedResult != null) {
    console.log('Cache hit for query: ' + nameQuery);
    return JSON.parse(cachedResult);
  }

  console.log('Cache miss for query: ' + nameQuery + '. Performing search...');
  const files = DriveApp.getFilesByType(MimeType.GOOGLE_SHEETS);
  const spreadsheets = [];
  while (files.hasNext()) {
    const file = files.next();
    if (nameQuery && file.getName().toLowerCase().includes(nameQuery.toLowerCase())) {
      spreadsheets.push({ id: file.getId(), name: file.getName() });
    }
  }

  cache.put(cacheKey, JSON.stringify(spreadsheets), 60 * 10); // 10分間キャッシュ

  return spreadsheets;
}

/**
 * 指定されたスプレッドシートIDのタイトルを取得します。
 * 取得できない場合はエラーをスローします。
 * @param {string} spreadsheetId タイトルを取得するスプレッドシートのID
 * @returns {string} スプレッドシートのタイトル
 * @throws {Error} スプレッドシートが見つからない場合やアクセスできない場合
 */
function getSpreadsheetTitle(spreadsheetId) {
  try {
    const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    return spreadsheet.getName();
  } catch (e) {
    throw new Error('指定されたID (' + spreadsheetId + ') のスプレッドシートが見つからないか、アクセスできません。' + e.message);
  }
}

/**
 * 選択されたスプレッドシートIDをユーザープロパティに保存します。
 * @param {string} spreadsheetId 保存するスプレッドシートのID
 */
function saveSelectedSpreadsheet(spreadsheetId) {
  PropertiesService.getUserProperties().setProperty('selectedSpreadsheetId', spreadsheetId);
  console.log('Selected Spreadsheet ID saved: ' + spreadsheetId);
}