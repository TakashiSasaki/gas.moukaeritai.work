/**
 * ウェブアプリのGETリクエスト用エントリーポイント
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Drive Shallow Mover')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/**
 * HTMLファイルの内容をインクルードするヘルパー関数
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
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
 * 現在のユーザーのメールアドレスを取得する
 */
function getCurrentUserEmail() {
  try {
    let email = Session.getActiveUser().getEmail();
    if (!email) {
      email = Session.getEffectiveUser().getEmail();
    }
    return email || "User (No Email Detected)";
  } catch (e) {
    return "Error: " + e.message;
  }
}

/**
 * 指定した親フォルダ内のサブフォルダ一覧と、そのフォルダまでのパスを取得する
 * @param {string} parentId 親フォルダID
 * @param {boolean} bypassCache キャッシュを無視するか
 * @return {Object} { items: Array, path: Array, fromCache: boolean }
 */
function getChildFolders(parentId = 'root', bypassCache = false) {
  const lock = LockService.getUserLock();
  try {
    if (!lock.tryLock(2000)) {
      throw new Error('SERVER_BUSY');
    }

    const cache = CacheService.getUserCache();
    // キャッシュキーを変更（データ構造が変わるため）
    const cacheKey = 'folder_data_v3_' + parentId;
    
    if (!bypassCache) {
      const cachedData = cache.get(cacheKey);
      if (cachedData) return JSON.parse(cachedData);
    }

    // 1. サブフォルダ一覧の取得
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
    
    const sortedFolders = folders.sort((a, b) => a.name.localeCompare(b.name));

    // 2. パンくずリスト（パス）の取得
    // parentId が root の場合は API 呼び出しを節約
    let path = [];
    if (parentId === 'root') {
      path = [{id: 'root', name: 'マイドライブ'}];
    } else {
      path = getFolderPathInternal(parentId);
      if (!path) {
        // 取得失敗時はとりあえずIDだけ返す
        path = [{id: parentId, name: 'Unknown Folder'}]; 
      }
    }

    const result = { items: sortedFolders, path: path, fromCache: false };
    
    // キャッシュに保存 (10分)
    try { cache.put(cacheKey, JSON.stringify({ ...result, fromCache: true }), 600); } catch (e) {}
    
    return result;

  } catch (e) {
    throw new Error('フォルダ取得エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * (内部関数) フォルダIDからルートまでのパス情報を取得
 */
function getFolderPathInternal(folderId) {
  const path = [];
  let currentId = folderId;
  
  // 無限ループ防止のため最大深度を設定
  for (let i = 0; i < 20; i++) {
    try {
      const file = Drive.Files.get(currentId, { fields: 'id, name, parents' });
      path.unshift({ id: file.id, name: file.name });
      
      if (!file.parents || file.parents.length === 0) break;
      currentId = file.parents[0];
    } catch (e) {
      break;
    }
  }
  return path;
}

/**
 * フォルダパスを文字列配列で取得（表示用API）
 */
function getFolderPath(folderId) {
  const pathStruct = getFolderPathInternal(folderId);
  if (!pathStruct || pathStruct.length === 0) return null;
  return pathStruct.map(f => f.name);
}

/**
 * ファイルサイズ整形
 */
function formatFileSize(sizeBytes) {
  if (!sizeBytes) return '-';
  const bytes = parseInt(sizeBytes);
  if (isNaN(bytes) || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  if (i < 0) return bytes + ' B';
  if (i >= sizes.length) return (bytes / Math.pow(k, sizes.length - 1)).toFixed(2) + ' ' + sizes[sizes.length - 1];
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 検索実行
 */
function searchFiles(q, pageToken = null, pageSize = 10) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');

  try {
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
      size: formatFileSize(file.size)
    }));
    return { files: files, nextPageToken: response.nextPageToken || null };
  } catch (e) {
    throw new Error('検索エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * ファイル一括取得
 */
function fetchFiles(q, initialPageToken, maxLimit = -1) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');

  try {
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
          size: formatFileSize(file.size)
        })));
      }
      pageToken = response.nextPageToken;
      if (maxLimit > 0 && allResults.length >= maxLimit) break;
    } while (pageToken);

    return { files: allResults, nextPageToken: pageToken || null };
  } catch (e) {
    throw new Error('取得エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * ファイル移動
 */
function moveFiles(fileIds, destinationId) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');

  try {
    const results = { success: 0, error: 0, details: [] };
    fileIds.forEach(fileId => {
      if (!fileId || fileId === 'on') return;
      try {
        const file = Drive.Files.get(fileId, { fields: 'parents' });
        const previousParents = (file.parents || []).join(',');
        Drive.Files.update({}, fileId, null, {
          addParents: destinationId,
          removeParents: previousParents
        });
        results.success++;
      } catch (e) {
        results.error++;
        results.details.push(`${e.message}`);
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
 * フォルダ内訳集計
 */
function getSingleFolderStats(folderId) {
  const cache = CacheService.getUserCache();
  const cacheKey = 'folder_stats_v2_' + folderId;
  const cachedData = cache.get(cacheKey);
  if (cachedData) return JSON.parse(cachedData);

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
          if (f.name && f.name.toLowerCase().endsWith('.md')) type = 'text/markdown';
          counts[type] = (counts[type] || 0) + 1;
        });
      }
      pageToken = response.nextPageToken;
    } while (pageToken);
    
    const result = { folderId: folderId, counts: counts };
    try { cache.put(cacheKey, JSON.stringify(result), 600); } catch (e) {}
    return result;
  } catch (e) {
    return { folderId: folderId, error: e.message };
  }
}