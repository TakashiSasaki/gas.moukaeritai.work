/**
 * @fileoverview Web App entry point. Serves the main HTML interface.
 */

/**
 * ユーザーがウェブアプリのURLにアクセスしたときにHTMLページを提供します。
 * Google Apps ScriptがWebアプリとして実行される際に、最初に呼び出す関数です。
 * @param {Object} e - イベントパラメータ。
 * @return {GoogleAppsScript.HTML.HtmlOutput} 生成されたHTMLページ。
 */
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('index')
      .setTitle('DNS Record Extractor')
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}