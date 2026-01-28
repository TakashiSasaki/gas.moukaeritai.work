/**
 * ウェブアプリのGETリクエスト用エントリーポイント
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Drive Query Builder & Mover')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * ユーザープロパティに設定を保存する
 */
function saveUserSettings(settings) {
  const userProperties = PropertiesService.getUserProperties();
  userProperties.setProperty('SEARCH_SETTINGS', JSON.stringify(settings));
}

/**
 * ユーザープロパティから設定を読み込む
 */
function loadUserSettings() {
  const userProperties = PropertiesService.getUserProperties();
  const settings = userProperties.getProperty('SEARCH_SETTINGS');
  return settings ? JSON.parse(settings) : {};
}

/**
 * 指定した親フォルダ内のサブフォルダ一覧を取得する（ピッカー用）
 * @param {string} parentId 親フォルダID
 * @return {Array} フォルダ情報の配列
 */
function getChildFolders(parentId = 'root') {
  try {
    const query = `'${parentId}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false`;
    const folders = [];
    let pageToken = null;

    do {
      const response = Drive.Files.list({
        q: query,
        pageToken: pageToken,
        fields: 'nextPageToken, files(id, name)',
        pageSize: 100
      });

      if (response.files) {
        folders.push(...response.files);
      }
      pageToken = response.nextPageToken;
    } while (pageToken);

    // 名前順にソート
    return folders.sort((a, b) => a.name.localeCompare(b.name));
  } catch (e) {
    throw new Error('フォルダ取得エラー: ' + e.message);
  }
}

/**
 * 組み立てられた q パラメータを使用してファイルを検索する
 */
function searchFiles(q) {
  try {
    const results = [];
    let pageToken = null;

    do {
      const response = Drive.Files.list({
        q: q,
        pageToken: pageToken,
        fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)',
        pageSize: 100
      });

      if (response.files && response.files.length > 0) {
        response.files.forEach(file => {
          results.push({
            id: file.id,
            name: file.name,
            mimeType: file.mimeType,
            modifiedTime: file.modifiedTime,
            size: file.size ? (parseInt(file.size) / 1024 / 1024).toFixed(2) + ' MB' : '-'
          });
        });
      }
      pageToken = response.nextPageToken;
    } while (pageToken);

    return results;
  } catch (e) {
    throw new Error('検索エラー: ' + e.message);
  }
}

/**
 * 選択されたファイル群を目的のフォルダに移動する
 */
function moveFiles(fileIds, destinationId) {
  if (!destinationId) throw new Error('移動先フォルダIDが指定されていません。');
  
  const results = {
    success: 0,
    error: 0,
    details: []
  };

  fileIds.forEach(fileId => {
    try {
      const file = Drive.Files.get(fileId, { fields: 'parents' });
      const previousParents = (file.parents || []).join(',');

      Drive.Files.update({}, fileId, {
        addParents: destinationId,
        removeParents: previousParents
      });
      
      results.success++;
    } catch (e) {
      results.error++;
      results.details.push(`Error moving ${fileId}: ${e.message}`);
    }
  });

  return results;
}