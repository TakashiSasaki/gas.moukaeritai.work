// ==========================================
// Storage.gs
// スプレッドシートの読み書きと自動管理を担当
// ==========================================

/**
 * スプレッドシートを取得します。存在しない場合や削除されている場合は新規作成します。
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet}
 */
function getOrCreateSpreadsheet() {
  const scriptProperties = PropertiesService.getScriptProperties();
  let spreadsheetId = scriptProperties.getProperty('SPREADSHEET_ID');
  let spreadsheet = null;

  // 1. プロパティに保存されたIDで開くことを試みる
  if (spreadsheetId) {
    try {
      spreadsheet = SpreadsheetApp.openById(spreadsheetId);
    } catch (e) {
      console.warn("以前のスプレッドシートが見つからないため、新規作成を準備します。");
      spreadsheetId = null;
    }
  }

  // 2. IDがない、またはファイルが開けなかった場合に新規作成
  if (!spreadsheet) {
    spreadsheet = SpreadsheetApp.create("Facility_HTML_Data_Store");
    scriptProperties.setProperty('SPREADSHEET_ID', spreadsheet.getId());
    
    // 初回シート設定
    const sheet = spreadsheet.getSheets()[0];
    sheet.setName("HTML_Data");
    // A:タイムスタンプ, B:PageID, C:施設名, D:HTML本文
    sheet.appendRow(["Timestamp", "PageID", "FacilityName", "HTMLContent"]);
    
    console.log("スプレッドシートを新規作成しました: " + spreadsheet.getId());
  } else {
    // 3. 必要なシートが存在するか確認
    let targetSheet = spreadsheet.getSheetByName("HTML_Data");
    if (!targetSheet) {
      targetSheet = spreadsheet.insertSheet("HTML_Data");
      targetSheet.appendRow(["Timestamp", "PageID", "FacilityName", "HTMLContent"]);
    }
  }
  return spreadsheet;
}

/**
 * 生成されたHTMLデータをスプレッドシートに追記保存します。
 * @param {number} pageId 施設のセット番号
 * @param {string} facilityName 施設名
 * @param {string} htmlContent 生成されたHTML文字列
 */
function saveHtmlData(pageId, facilityName, htmlContent) {
  const ss = getOrCreateSpreadsheet();
  const sheet = ss.getSheetByName("HTML_Data");
  sheet.appendRow([new Date(), pageId, facilityName, htmlContent]);
}

/**
 * 特定の施設IDの最新のHTMLコンテンツを返します。
 * @param {number} pageId 施設のセット番号
 * @return {string|null} HTML文字列（データがない場合はnull）
 */
function getLatestHtml(pageId) {
  const ss = getOrCreateSpreadsheet();
  const sheet = ss.getSheetByName("HTML_Data");
  const data = sheet.getDataRange().getValues();
  
  // 下から上（最新から過去）へ向かって検索
  for (let i = data.length - 1; i > 0; i--) {
    if (data[i][1] == pageId) {
      return data[i][3]; // D列のHTML
    }
  }
  return null;
}

/**
 * 全ての施設の最新取得日時をオブジェクト形式で取得します。
 * @return {Object} { 1: "2024/05/20 01:00:00", 2: ... }
 */
function getLatestTimestamps() {
  const ss = getOrCreateSpreadsheet();
  const sheet = ss.getSheetByName("HTML_Data");
  const data = sheet.getDataRange().getValues();
  const timestamps = {};

  // 2行目以降を走査（1行目はヘッダー）
  for (let i = 1; i < data.length; i++) {
    const ts = data[i][0];
    const pageId = data[i][1];
    
    if (ts instanceof Date) {
      // スプレッドシートの後ろ（下）にある行ほど新しい
      // 順次上書きしていくことで、最終的に最新の日時が残る
      timestamps[pageId] = Utilities.formatDate(ts, "JST", "yyyy/MM/dd HH:mm:ss");
    }
  }
  return timestamps;
}