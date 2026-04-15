document.addEventListener("DOMContentLoaded", () => {
  const findTab = document.getElementById("find-tab");
  const findIframe = document.getElementById("find-iframe");

  const resizeIframe = () => {
    if (!findIframe) {
      return;
    }

    try {
      const iframeDoc = findIframe.contentWindow.document;
      if (!iframeDoc.body) {
        return;
      }

      findIframe.style.height = `${iframeDoc.body.scrollHeight}px`;

      const resizeObserver = new ResizeObserver(() => {
        findIframe.style.height = `${iframeDoc.body.scrollHeight}px`;
      });
      resizeObserver.observe(iframeDoc.body);
    } catch (error) {
      console.log("Cross-origin iframe access restricted or content not loaded yet.");
    }
  };

  if (findTab) {
    findTab.addEventListener("shown.bs.tab", resizeIframe);
  }

  if (findIframe) {
    findIframe.addEventListener("load", resizeIframe);
  }
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch((error) => {
      console.log("ServiceWorker registration failed:", error);
    });
  });
}
