// ==========================================
// Gemini.gs
// Gemini API の操作（システムインストラクション追加版）
// ==========================================

function generateFacilityHtml(targetPrompt) {
  const apiKey = PropertiesService.getScriptProperties().getProperty("GEMINI_API_KEY");
  const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/${MODEL_NAME}:generateContent?key=${apiKey}`;

  const contents = [
    {
      "role": "user",
      "parts": [{ "text": targetPrompt }]
    }
  ];

  const payload = {
    // ----------------------------------------------------
    // ▼ 追加：Geminiへの強い基本ルール（システムインストラクション）
    // ----------------------------------------------------
    "systemInstruction": {
      "parts": [
        {
          "text": "あなたは提供されたURLから展示スケジュールなどの情報を読み取り、美しく整理された静的なHTMLを出力するアシスタントです。以下のルールを厳守してください。\n1. JavaScriptを用いたデータの動的取得(fetch等)やスクレイピングを行うコードは絶対に記述しないでください。\n2. あなた自身がURLから読み取った具体的な展示名、日付、場所などの情報を、直接HTMLのタグ内にテキストとして静的に書き込んでください。\n3. ローディング表示などは不要です。\n4. デザインはCSS(styleタグ)を用いて美しく装飾してください。施設の公式なウェブサイトへのリンクをヘッダとフッタに含めてください。スマートフォンの縦長の画面にも対応するようにレスポンシブなデザインにしてください。"
        }
      ]
    },
    // ----------------------------------------------------
    "contents": contents,
    "generationConfig": {
      "temperature": 0.4, // 温度を少し下げて、より指示に忠実に（クリエイティブになりすぎないように）します
      "topP": 0.95,
      "topK": 40,
      "maxOutputTokens": 8192
    }
  };

  const options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };

  const response = UrlFetchApp.fetch(endpoint, options);
  const result = JSON.parse(response.getContentText());
  
  if (result.error) {
    throw new Error("Gemini API Error: " + result.error.message);
  }

  const parts = result.candidates[0].content.parts;
  let rawResponseText = parts[parts.length - 1].text;
  
  // 正規表現によるHTML抽出ロジック（そのまま維持）
  const htmlMatch = rawResponseText.match(/(?:<!DOCTYPE html>|<html)[^]*?<\/html>/i);

  if (htmlMatch) {
    return htmlMatch[0]; 
  } else {
    console.warn("HTMLタグが検出されませんでした。");
    return rawResponseText.replace(/^```(html)?\n?/gm, '').replace(/```$/gm, '').trim();
  }
}