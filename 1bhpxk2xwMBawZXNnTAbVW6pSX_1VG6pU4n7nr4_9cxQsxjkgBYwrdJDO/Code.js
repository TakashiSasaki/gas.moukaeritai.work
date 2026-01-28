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
 * ファイルサイズを適切な単位に整形するヘルパー関数
 * @param {string|number} sizeBytes バイト数
 * @return {string} 整形されたサイズ文字列
 */
function formatFileSize(sizeBytes) {
  if (!sizeBytes) return '-';
  const bytes = parseInt(sizeBytes);
  if (isNaN(bytes) || bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  // 単位配列の範囲外アクセス防止
  if (i < 0) return bytes + ' B';
  if (i >= sizes.length) return (bytes / Math.pow(k, sizes.length - 1)).toFixed(2) + ' ' + sizes[sizes.length - 1];

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 組み立てられた q パラメータを使用してファイルを検索する
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
      size: formatFileSize(file.size) // ヘルパー関数を使用
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
    lock.waitLock(60000);
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
          size: formatFileSize(file.size) // ヘルパー関数を使用
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

/**
 * 指定したフォルダ単体のアイテム数（種別ごとの内訳）を集計する
 * キャッシュを活用してAPI呼び出し回数を削減
 * @param {string} folderId 集計対象のフォルダID
 */
function getSingleFolderStats(folderId) {
  const cache = CacheService.getUserCache();
  const cacheKey = 'folder_stats_v2_' + folderId;
  
  const cachedData = cache.get(cacheKey);
  if (cachedData) {
    return JSON.parse(cachedData);
  }

  const counts = {};
  let pageToken = null;
  
  try {
    do {
      const response = Drive.Files.list({
        q: `'${folderId}' in parents and trashed = false`,
        pageToken: pageToken,
        fields: 'nextPageToken, files(mimeType, name)', 
        pageSize: 1000
      });
      
      if (response.files) {
        response.files.forEach(f => {
          let type = f.mimeType;
          if (f.name && f.name.toLowerCase().endsWith('.md')) {
            type = 'text/markdown';
          }
          
          counts[type] = (counts[type] || 0) + 1;
        });
      }
      pageToken = response.nextPageToken;
    } while (pageToken);
    
    const result = { folderId: folderId, counts: counts };
    
    try {
      cache.put(cacheKey, JSON.stringify(result), 600);
    } catch (e) {
      console.warn('Stats cache storage failed: ' + e.message);
    }
    
    return result;
  } catch (e) {
    return { folderId: folderId, error: e.message };
  }
}