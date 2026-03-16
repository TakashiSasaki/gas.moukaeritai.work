// ==========================================
// Main.gs
// Webアプリのルーティングと実行制御を担当
// ==========================================

/**
 * Webアプリにアクセスした際に実行される関数
 * @param {Object} e HTTPリクエストのパラメータ
 */
function doGet(e) {
  const pageId = e.parameter.page;
  
  // 1. pageパラメータがあり、かつ有効な施設IDの場合
  if (pageId && FACILITY_CONFIG[pageId]) {
    const htmlContent = getLatestHtml(pageId);
    
    if (htmlContent) {
      // スプレッドシートから取得した最新のHTMLをそのまま表示
      return HtmlService.createHtmlOutput(htmlContent)
        .setTitle(FACILITY_CONFIG[pageId].name + " - 最新レポート")
        .addMetaTag('viewport', 'width=device-width, initial-scale=1');
    } else {
      // データが存在しない場合のメッセージ
      return HtmlService.createHtmlOutput("<h1>まだデータが取得されていません。</h1><p>一覧に戻って「データ作成」を行ってください。</p>");
    }
  } 
  
  // 2. パラメータがない、または不正な場合は「施設情報レポート一覧」を表示
  else {
    const template = HtmlService.createTemplateFromFile('index');
    
    // テンプレートに渡す変数を設定
    template.webAppUrl = ScriptApp.getService().getUrl();
    template.facilities = FACILITY_CONFIG;
    
    // スプレッドシート情報の取得
    const ss = getOrCreateSpreadsheet();
    template.ssUrl = ss.getUrl();
    
    // Storage.gs から最新の取得日時リストを取得
    template.timestamps = getLatestTimestamps();
    
    return template.evaluate()
      .setTitle("施設情報レポート一覧")
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
  }
}

/**
 * データの取得から保存までを一貫して実行するコア関数
 * @param {number} pageId 施設のセット番号
 */
function executeAndSave(pageId) {
  const config = FACILITY_CONFIG[pageId];
  if (!config) return;

  try {
    console.log(`開始: ${config.name} (ID: ${pageId}) のデータ生成中...`);
    
    // Gemini.gs の関数を呼び出してHTMLを生成
    const generatedHtml = generateFacilityHtml(config.prompt);
    
    // Storage.gs の関数を呼び出してスプレッドシートに保存
    saveHtmlData(pageId, config.name, generatedHtml);
    
    console.log(`成功: ${config.name} の保存が完了しました。`);
  } catch (error) {
    console.error(`エラー: ID ${pageId} の処理中に問題が発生しました。`, error);
    throw error; // エラーを上位に投げてWeb側のハンドラに伝える
  }
}

/**
 * Web画面(index.html)のボタンから呼び出される連携関数
 * @param {number} pageId 施設のセット番号
 */
function triggerUpdateFromWeb(pageId) {
  const config = FACILITY_CONFIG[pageId];
  if (!config) throw new Error("無効な施設IDです。");
  
  try {
    executeAndSave(pageId);
    return `${config.name} のデータを更新しました。`;
  } catch (e) {
    throw new Error(`${config.name} の更新に失敗しました: ${e.message}`);
  }
}

// ==========================================
// 定期実行（時間主導型トリガー）用エントリーポイント
// ==========================================
// 以下の各関数を GAS エディタの「トリガー」メニューから
// それぞれ毎日指定の時刻（午前1時〜10時など）に実行するよう設定してください。

function triggerSet1()  { executeAndSave(1); }
function triggerSet2()  { executeAndSave(2); }
function triggerSet3()  { executeAndSave(3); }
function triggerSet4()  { executeAndSave(4); }
function triggerSet5()  { executeAndSave(5); }
function triggerSet6()  { executeAndSave(6); }
function triggerSet7()  { executeAndSave(7); }
function triggerSet8()  { executeAndSave(8); }
function triggerSet9()  { executeAndSave(9); }
function triggerSet10() { executeAndSave(10); }