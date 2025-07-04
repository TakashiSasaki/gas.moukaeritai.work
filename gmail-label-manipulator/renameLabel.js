function renameLabel(){
  var lock = LockService.getUserLock();
  lock.waitLock(10000);
  var range = SpreadsheetApp.getActiveRange();
  if(range.getWidth()<2) {
    throw "the width of active range should be more than or qeual to two.";
  }//if
  for(var i=1; i<=range.getHeight(); ++i){
    var srcLabelName = range.getCell(i,1).getValue();
    var srcLabel = GmailApp.getUserLabelByName(srcLabelName);
    var dstLabelName = range.getCell(i, range.getWidth()).getValue();
    var dstLabel = GmailApp.getUserLabelByName(dstLabelName);
    for(;;){
      var threads = srcLabel.getThreads(0, 100);
      if(threads.length == 0) {
        break;
      }//if
      dstLabel.addToThreads(threads);
      srcLabel.removeFromThreads(threads);
    }//for
  }//for
  lock.releaseLock();
}//renameLabel

function _testRenameLabel(){
  var spreadsheetUrl = "https://docs.google.com/spreadsheets/d/1lWjTl1UfoOa0ayohCV5kScy0T0HtMWJgWMCLrmIwsuU/edit?addon_dry_run=AAnXSK-HxpkNe08HkEbcsa_cSIZ95apz2eq0euZDq1HYpU4-gzPlbu9DPnSnz960N1dSSeSHgJ5SjKg4UFShzGMr_ulAOfaVvCoQOJIBoDV6EigJtxEcCm4Zy5iAx-KLiCGxuh5s-3Rf#gid=0";
  var sheetName = "シート1";
  var spreadsheet = SpreadsheetApp.openByUrl(spreadsheetUrl);
  SpreadsheetApp.setActiveSpreadsheet(spreadsheet);
  var sheet = spreadsheet.getSheetByName(sheetName);
  spreadsheet.setActiveSheet(sheet);
  var range = sheet.getRange(1, 1, 1, 2);
  sheet.setActiveRange(range);  
  renameLabel();
}//_testRenameLabel
