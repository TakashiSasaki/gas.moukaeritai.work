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
 * @return {Object} { items: Array, fromCache: boolean }
 */
function getChildFolders(parentId = 'root', bypassCache = false) {
  const lock = LockService.getUserLock();
  try {
    lock.waitLock(10000);
    const cache = CacheService.getUserCache();
    const cacheKey = 'folder_children_' + parentId;
    if (!bypassCache) {
      const cachedData = cache.get(cacheKey);
      if (cachedData) return { items: JSON.parse(cachedData), fromCache: true };
    }
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
      if (response.files) folders.push(...response.files);
      pageToken = response.nextPageToken;
    } while (pageToken);
    const result = folders.sort((a, b) => a.name.localeCompare(b.name));
    try { cache.put(cacheKey, JSON.stringify(result), 600); } catch (e) {}
    return { items: result, fromCache: false };
  } catch (e) {
    throw new Error('フォルダ取得エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * 組み立てられた q パラメータを使用してファイルを検索する（プレビュー用/ページング対応）
 * @param {string} q 検索クエリ
 * @param {string} pageToken 次のページを取得するためのトークン
 * @param {number} pageSize 取得件数
 */
function searchFiles(q, pageToken = null, pageSize = 10) {
  const lock = LockService.getUserLock();
  try {
    lock.waitLock(30000);
    const response = Drive.Files.list({
      q: q,
      pageToken: pageToken,
      fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)',
      pageSize: pageSize
    });
    const files = (response.files || []).map(file => ({
      id: file.id,
      name: file.name,
      mimeType: file.mimeType,
      modifiedTime: file.modifiedTime,
      size: file.size ? (parseInt(file.size) / 1024 / 1024).toFixed(2) + ' MB' : '-'
    }));
    return {
      files: files,
      nextPageToken: response.nextPageToken || null
    };
  } catch (e) {
    throw new Error('検索エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * 特定のトークンから残りのファイルをすべて一括取得する
 */
function fetchAllRemaining(q, initialPageToken) {
  const lock = LockService.getUserLock();
  try {
    lock.waitLock(60000); // 重い可能性があるため長めに待機
    const allResults = [];
    let pageToken = initialPageToken;
    do {
      const response = Drive.Files.list({
        q: q,
        pageToken: pageToken,
        fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)',
        pageSize: 100
      });
      if (response.files) {
        allResults.push(...response.files.map(file => ({
          id: file.id,
          name: file.name,
          mimeType: file.mimeType,
          modifiedTime: file.modifiedTime,
          size: file.size ? (parseInt(file.size) / 1024 / 1024).toFixed(2) + ' MB' : '-'
        })));
      }
      pageToken = response.nextPageToken;
    } while (pageToken);
    return allResults;
  } catch (e) {
    throw new Error('一括取得エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * 選択されたファイル群を目的のフォルダに移動する
 */
function moveFiles(fileIds, destinationId) {
  const lock = LockService.getUserLock();
  try {
    lock.waitLock(30000);
    const results = { success: 0, error: 0, details: [] };
    fileIds.forEach(fileId => {
      try {
        const file = Drive.Files.get(fileId, { fields: 'parents' });
        const previousParents = (file.parents || []).join(',');
        Drive.Files.update({}, fileId, { addParents: destinationId, removeParents: previousParents });
        results.success++;
      } catch (e) {
        results.error++;
        results.details.push(`Error moving ${fileId}: ${e.message}`);
      }
    });
    return results;
  } catch (e) {
    throw new Error('移動処理エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}