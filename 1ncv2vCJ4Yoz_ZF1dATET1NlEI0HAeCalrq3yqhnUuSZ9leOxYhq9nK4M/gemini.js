/**
 * @fileoverview
 * Gemini APIを利用してDNS設定のスクリーンショットからレコードを抽出するコアロジック。
 * このファイルには、ウェブアプリから呼び出されるメイン関数と、そのヘルパー関数が含まれます。
 */

// --- Configuration ---
const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');


// =================================================================
// WEB APPLICATION BACKEND
// =================================================================

/**
 * [Web App用] ブラウザから送信されたBase64エンコードの画像データを処理します。
 * スクリプト全体で同時に1つのプロセスのみ実行されるようにLockServiceで排他制御を行います。
 * @param {string} base64Data 画像ファイルのData URL (Base64エンコード)。
 * @param {string} mimeType 画像のMIMEタイプ (例: 'image/png')。
 * @param {string} fileName 元のファイル名。
 * @return {string} 抽出されたDNSレコードのJSON文字列。
 */
function extractDnsRecordsFromImages(arrayOfBase64Data, arrayOfMimeTypes, arrayOfFileNames) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    throw new Error('サーバーが現在他のリクエストを処理中です。しばらく待ってからもう一度お試しください。');
  }

  try {
    const startTime = new Date();
    Logger.log(`[WebApp START] ${startTime.toLocaleTimeString()}: Execution started for ${arrayOfFileNames.length} files.`);
    
    // 全てのファイルを順番にアップロード
    const geminiFiles = [];
    for (let i = 0; i < arrayOfBase64Data.length; i++) {
      Logger.log(`[WebApp] Uploading file ${i + 1}/${arrayOfBase64Data.length}: ${arrayOfFileNames[i]}`);
      const blob = Utilities.newBlob(Utilities.base64Decode(arrayOfBase64Data[i].split(',')[1]), arrayOfMimeTypes[i], arrayOfFileNames[i]);
      const uploadedFile = uploadBlobToGemini(blob);
      geminiFiles.push(uploadedFile);
    }
    Logger.log(`[WebApp] ${new Date().toLocaleTimeString()}: All files uploaded. Time elapsed: ${(new Date() - startTime) / 1000}s.`);

    // Gemini APIに送信するリクエストのparts配列を構築
    const prompt = getPrompt();
    const parts = [{ text: prompt }];
    geminiFiles.forEach(file => {
      parts.push({
        fileData: { mimeType: file.mimeType, fileUri: file.uri }
      });
    });

    const generationConfig = { temperature: 0.1, responseMimeType: 'application/json' };
    const data = { generationConfig, contents: [{ role: 'user', parts: parts }] };
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key=${apiKey}`;
    const options = {
      method: 'POST',
      contentType: 'application/json',
      payload: JSON.stringify(data),
      muteHttpExceptions: true,
    };

    Logger.log(`[WebApp] ${new Date().toLocaleTimeString()}: Sending content generation request for ${geminiFiles.length} images.`);
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    Logger.log(`[WebApp] ${new Date().toLocaleTimeString()}: Received response (Code: ${responseCode}).`);

    if (responseCode !== 200) throw new Error(`API request failed with status code ${responseCode}.`);
    
    const responseObject = JSON.parse(responseText);
    if (!responseObject.candidates || responseObject.candidates.length === 0) {
      throw new Error('Invalid API response: "candidates" field is missing.');
    }
    
    const content = responseObject.candidates[0].content.parts[0].text;
    Logger.log(`[WebApp END] ${new Date().toLocaleTimeString()}: Execution finished successfully.`);
    return content;

  } catch (e) {
    Logger.log(`[WebApp ERROR] Error details: ${e.toString()}`);
    throw new Error(`Server-side error: ${e.message}`);
  } finally {
    lock.releaseLock();
    Logger.log(`[WebApp] Lock released.`);
  }
}

// =================================================================
// CORE & HELPER FUNCTIONS
// =================================================================

/**
 * Gemini APIに送信するプロンプトを生成します。
 * @return {string} プロンプトテキスト。
 */
function getPrompt() {
  return `
添付画像はDNS管理画面のスクリーンショットです。この画像に対してOCRを実行し、表示されているすべてのDNSレコードを抽出してください。
各レコードについて、以下のフィールドを特定してください：
- type: レコードのタイプ (例: A, CNAME, MX, TXT)
- hostname: ホスト名 (または名前、サブドメイン)
- value: 値 (または内容、データ、参照先)
- ttl: TTL (Time To Live)
- priority: 優先度 (MXレコードなど、該当する場合のみ)

抽出した情報は、JSON配列形式で出力してください。配列内の各オブジェクトが、単一のDNSレコードを表すようにしてください。レスポンスには、指定されたJSON配列のコードブロックのみを含め、それ以外の説明文や前置きは一切含めないでください。
`;
}

/**
 * BlobデータをGeminiにアップロードし、ファイルが利用可能になるまでポーリングします。
 * @param {GoogleAppsScript.Base.Blob} blob アップロードするBlobオブジェクト。
 * @return {object} ACTIVE状態になったGeminiファイルリソース。
 */
function uploadBlobToGemini(blob) {
  const mimeType = blob.getContentType();
  Logger.log(`[Uploader] Starting upload for blob: ${blob.getName()} (${mimeType})`);

  const uploadUrl = `https://generativelanguage.googleapis.com/upload/v1beta/files?key=${apiKey}`;
  const uploadOptions = {
    method: 'POST',
    headers: { 'X-Goog-Upload-Protocol': 'raw', 'Content-Type': mimeType },
    payload: blob.getBytes(),
    muteHttpExceptions: true,
  };

  const uploadResponse = UrlFetchApp.fetch(uploadUrl, uploadOptions);
  if (uploadResponse.getResponseCode() !== 200) {
    throw new Error(`File upload failed. Response: ${uploadResponse.getContentText()}`);
  }

  let geminiFile = JSON.parse(uploadResponse.getContentText()).file;
  Logger.log(`[Uploader] File uploaded. Gemini name: ${geminiFile.name}, State: ${geminiFile.state}`);

  const fileApiUrl = `https://generativelanguage.googleapis.com/v1beta/files/${geminiFile.name}?key=${apiKey}`;
  for (let i = 0; i < 10; i++) {
    if (geminiFile.state === 'ACTIVE') {
      Logger.log('[Uploader] File is now ACTIVE.');
      return geminiFile;
    }
    Utilities.sleep(3000);
    Logger.log(`[Uploader] Polling attempt ${i + 1}...`);
    const pollResponse = UrlFetchApp.fetch(fileApiUrl);
    geminiFile = JSON.parse(pollResponse.getContentText()).file;
  }
  
  throw new Error(`File processing timed out. Final state: ${geminiFile.state}`);
}

// =================================================================
// EDITOR TEST FUNCTIONS (for development)
// =================================================================

// /**
//  * [Editor用] Google Drive上のファイルを指定してテストを実行します。
//  */
// function runTestFromEditor() {
//   try {
//     Logger.log('--- Starting Editor Test ---');
//     const fileName = 'onamae.jpeg'; // !!! Google Driveにあるテスト用のファイル名に変更してください
//     const file = getFileFromDrive(fileName);
//     if (!file) throw new Error(`File not found: ${fileName}`);

//     const resultJson = extractDnsRecordsFromImage(
//       `data:${file.getMimeType()};base64,${Utilities.base64Encode(file.getBlob().getBytes())}`,
//       file.getMimeType(),
//       file.getName()
//     );
    
//     const dnsRecords = JSON.parse(resultJson);
//     Logger.log('--- Parsed DNS Records (JavaScript Object) ---');
//     console.log(dnsRecords);
//     Logger.log(`--- Test finished successfully. Extracted ${dnsRecords.length} records. ---`);
    
//   } catch (e) {
//     Logger.log('--- An error occurred during the editor test ---');
//     Logger.log('Error: %s', e.toString());
//   }
// }

/**
 * [Editor用] Google Driveからファイルを名前で取得します。
 * @param {string} fileName 取得するファイル名。
 * @return {GoogleAppsScript.Drive.File | null} 見つかったファイルオブジェクト。
 */
// function getFileFromDrive(fileName) {
//   const files = DriveApp.searchFiles(`title = "${fileName}" and trashed = false`);
//   return files.hasNext() ? files.next() : null;
// }