/**
 * フォルダIDから親フォルダIDを取得するヘルパー
 */
function getParentId(folderId) {
  try {
    const file = Drive.Files.get(folderId, { fields: 'parents' });
    if (file.parents && file.parents.length > 0) {
      return file.parents[0];
    }
  } catch (e) {
    console.warn('Failed to fetch parent for: ' + folderId);
  }
  return 'root';
}

/**
 * (既存のコードも含め、完全なサーバーサイドロジック)
 */
function doGet() {
  return HtmlService.createTemplateFromFile('Index')
    .evaluate()
    .setTitle('Drive Shallow Mover')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

function saveUserSettings(settings) {
  PropertiesService.getUserProperties().setProperty('SEARCH_SETTINGS', JSON.stringify(settings));
}

function loadUserSettings() {
  const settings = PropertiesService.getUserProperties().getProperty('SEARCH_SETTINGS');
  return settings ? JSON.parse(settings) : {};
}

function getCurrentUserEmail() {
  try {
    let email = Session.getActiveUser().getEmail() || Session.getEffectiveUser().getEmail();
    return email || "User";
  } catch (e) { return "Error: " + e.message; }
}

function getChildFolders(parentId = 'root', bypassCache = false) {
  const lock = LockService.getUserLock();
  try {
    if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');
    const cache = CacheService.getUserCache();
    const cacheKey = 'folder_data_v3_' + parentId;
    if (!bypassCache) {
      const cachedData = cache.get(cacheKey);
      if (cachedData) return JSON.parse(cachedData);
    }
    const query = `'${parentId}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false`;
    const folders = [];
    let pageToken = null;
    do {
      const response = Drive.Files.list({ q: query, pageToken: pageToken, fields: 'nextPageToken, files(id, name)', pageSize: 100 });
      if (response.files) folders.push(...response.files);
      pageToken = response.nextPageToken;
    } while (pageToken);
    const sortedFolders = folders.sort((a, b) => a.name.localeCompare(b.name));
    let path = [];
    if (parentId === 'root') {
      path = [{id: 'root', name: 'マイドライブ'}];
    } else {
      path = getFolderPathInternal(parentId);
      if(!path) path = [{id: parentId, name: 'Unknown'}];
    }
    const result = { items: sortedFolders, path: path, fromCache: false };
    try { cache.put(cacheKey, JSON.stringify({ ...result, fromCache: true }), 600); } catch (e) {}
    return result;
  } catch (e) {
    throw new Error('フォルダ取得エラー: ' + e.message);
  } finally { lock.releaseLock(); }
}

function getFolderPathInternal(folderId) {
  const path = [];
  let currentId = folderId;
  for (let i = 0; i < 20; i++) {
    try {
      const file = Drive.Files.get(currentId, { fields: 'id, name, parents' });
      path.unshift({ id: file.id, name: file.name });
      if (!file.parents || file.parents.length === 0) break;
      currentId = file.parents[0];
    } catch (e) { break; }
  }
  return path.length > 0 ? path : null;
}

function getFolderPath(folderId) {
  const pathStruct = getFolderPathInternal(folderId);
  return pathStruct ? pathStruct.map(f => f.name) : null;
}

function formatFileSize(sizeBytes) {
  if (!sizeBytes) return '-';
  const bytes = parseInt(sizeBytes);
  if (isNaN(bytes) || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function searchFiles(q, pageToken = null, pageSize = 10) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');
  try {
    const response = Drive.Files.list({ q: q, pageToken: pageToken, fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)', pageSize: pageSize });
    const files = (response.files || []).map(file => ({ id: file.id, name: file.name, mimeType: file.mimeType, modifiedTime: file.modifiedTime, size: formatFileSize(file.size) }));
    return { files: files, nextPageToken: response.nextPageToken || null };
  } catch (e) { throw new Error('検索エラー: ' + e.message); } finally { lock.releaseLock(); }
}

function fetchFiles(q, initialPageToken, maxLimit = -1) {
  const lock = LockService.getUserLock();
  if (!lock.tryLock(2000)) throw new Error('SERVER_BUSY');
  try {
    const allResults = [];
    let pageToken = initialPageToken;
    do {
      const response = Drive.Files.list({ q: q, pageToken: pageToken, fields: 'nextPageToken, files(id, name, mimeType, modifiedTime, size)', pageSize: 100 });
      if (response.files) {
        allResults.push(...response.files.map(file => ({ id: file.id, name: file.name, mimeType: file.mimeType, modifiedTime: file.modifiedTime, size: formatFileSize(file.size) })));
      }
      pageToken = response.nextPageToken;
      if (maxLimit > 0 && allResults.length >= maxLimit) break;
    } while (pageToken);
    return { files: allResults, nextPageToken: pageToken || null };
  } catch (e) { throw new Error('取得エラー: ' + e.message); } finally { lock.releaseLock(); }
}

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
        Drive.Files.update({}, fileId, null, { addParents: destinationId, removeParents: previousParents });
        results.success++;
      } catch (e) { results.error++; results.details.push(`${e.message}`); }
    });
    return results;
  } catch (e) { throw new Error('移動処理エラー: ' + e.message); } finally { lock.releaseLock(); }
}

function getSingleFolderStats(folderId) {
  const cache = CacheService.getUserCache();
  const cacheKey = 'folder_stats_v2_' + folderId;
  const cachedData = cache.get(cacheKey);
  if (cachedData) return JSON.parse(cachedData);
  const counts = {};
  let pageToken = null;
  try {
    do {
      const response = Drive.Files.list({ q: `'${folderId}' in parents and trashed = false`, pageToken: pageToken, fields: 'nextPageToken, files(mimeType, name)', pageSize: 1000 });
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
  } catch (e) { return { folderId: folderId, error: e.message }; }
}