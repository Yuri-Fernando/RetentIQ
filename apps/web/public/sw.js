// idea dev #5 "Aplicação PWA offline" — service worker simples, cache-first, das
// rotas estáticas principais (login e shell do dashboard). Implementação manual (sem
// next-pwa/workbox) para não adicionar dependência nova num ambiente de instalação
// já problemático — ver docs/HISTORICO.md.
//
// IMPORTANTE: este SW cobre apenas VISUALIZAÇÃO offline (a última tela cacheada
// renderiza sem rede). Qualquer ação que precise de rede — login, criar/mover cards
// do kanban, comentários, recomendações — continua exigindo conexão; não há fila de
// sincronização/replay de escrita offline nesta versão.

const CACHE_NAME = "retentiq-shell-v1";
const PRECACHE_URLS = ["/", "/dashboard"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Só intercepta navegação GET (HTML) — chamadas de API continuam indo direto pra
  // rede, sempre, pra nunca servir dados de retenção/churn desatualizados por engano.
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request)
        .then((response) => {
          if (response.ok && PRECACHE_URLS.includes(url.pathname)) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match("/"));
    })
  );
});
