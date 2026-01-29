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
 * これがないと <?!= include('JavaScript'); ?> が動作しません
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
 * 指定した親フォルダ内のサブフォルダ一覧を取得する（ピッカー用）
 */
function getChildFolders(parentId = 'root', bypassCache = false) {
  const lock = LockService.getUserLock();
  try {
    if (!lock.tryLock(2000)) {
      throw new Error('SERVER_BUSY');
    }

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
 * フォルダIDからルートまでのパス（フォルダ名の配列）を取得する
 */
function getFolderPath(folderId) {
  if (!folderId) return null;
  
  const cache = CacheService.getUserCache();
  const cacheKey = 'folder_path_v1_' + folderId;
  const cached = cache.get(cacheKey);
  if (cached) return JSON.parse(cached);

  const path = [];
  let currentId = folderId;
  
  for (let i = 0; i < 20; i++) {
    try {
      const file = Drive.Files.get(currentId, { fields: 'id, name, parents' });
      path.unshift(file.name);
      if (!file.parents || file.parents.length === 0) break; 
      currentId = file.parents[0];
    } catch (e) {
      if (path.length === 0) return null;
      break; 
    }
  }
  
  try { cache.put(cacheKey, JSON.stringify(path), 300); } catch (e) {}
  return path;
}

/**
 * ファイルサイズを適切な単位に整形するヘルパー関数
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
 * 組み立てられた q パラメータを使用してファイルを検索する
 */
function searchFiles(q, pageToken = null, pageSize = 10) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) {
    throw new Error('SERVER_BUSY');
  }

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
 * 続きのファイルを指定件数分取得する
 */
function fetchFiles(q, initialPageToken, maxLimit = -1) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) {
    throw new Error('SERVER_BUSY');
  }

  try {
    const allResults = [];
    let pageToken = initialPageToken;
    let limitReached = false;
    
    do {
      const response = Drive.Files.list({
        q: q,
        pageToken: pageToken,
        fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)',
        pageSize: 100
      });
      
      if (response.files) {
        const formattedFiles = response.files.map(file => ({
          id: file.id,
          name: file.name,
          mimeType: file.mimeType,
          modifiedTime: file.modifiedTime,
          size: formatFileSize(file.size)
        }));
        
        if (maxLimit > 0) {
          const remainingSlots = maxLimit - allResults.length;
          if (formattedFiles.length > remainingSlots) {
            allResults.push(...formattedFiles.slice(0, remainingSlots));
          } else {
             allResults.push(...formattedFiles);
          }
        } else {
           allResults.push(...formattedFiles);
        }
      }
      
      pageToken = response.nextPageToken;

      if (maxLimit > 0 && allResults.length >= maxLimit) {
        limitReached = true;
        break;
      }
      
    } while (pageToken);

    return {
      files: allResults,
      nextPageToken: pageToken || null
    };
    
  } catch (e) {
    throw new Error('取得エラー: ' + e.message);
  } finally {
    lock.releaseLock();
  }
}

/**
 * 選択されたファイル群を目的のフォルダに移動する
 */
function moveFiles(fileIds, destinationId) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) {
    throw new Error('SERVER_BUSY');
  }

  try {
    const results = { success: 0, error: 0, details: [] };
    fileIds.forEach(fileId => {
      if (!fileId || fileId === 'on') {
        results.error++;
        results.details.push(`Invalid ID: ${fileId}`);
        return;
      }

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
 * 指定したフォルダ単体のアイテム数（種別ごとの内訳）を集計する
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