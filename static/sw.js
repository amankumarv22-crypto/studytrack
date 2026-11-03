const C = "studytrack-v2";
self.addEventListener("install", e => {
  e.waitUntil(caches.open(C).then(c => c.addAll(["/static/style.css", "/static/icon-192.png"])));
  self.skipWaiting();
});
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
  } else {
    e.respondWith(fetch(e.request).catch(() => new Response(
      "<h2 style='font-family:sans-serif;text-align:center;margin-top:30vh'>You are offline.<br>Reconnect to use StudyTrack.</h2>",
      {headers: {"Content-Type": "text/html"}})));
  }
});
