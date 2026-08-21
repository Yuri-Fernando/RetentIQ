import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";

// idea dev #5 "Aplicação PWA offline": manifest + theme-color entram pelo próprio
// `metadata` do App Router (SSR-safe, sem precisar de client component aqui).
export const metadata: Metadata = {
  title: "RetentIQ",
  description: "Plataforma full-stack de inteligência de receita e retenção de clientes.",
  manifest: "/manifest.json",
};

// Next.js 14.2+ move themeColor de `metadata` para `viewport` (metadata.themeColor
// está deprecated e emite warning em build).
export const viewport: Viewport = {
  themeColor: "#0a0a0a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        {children}
        {/* Registro do service worker (public/sw.js) via next/script, afterInteractive:
            roda só no client, depois da hidratação, sem afetar o SSR das páginas. */}
        <Script id="sw-register" strategy="afterInteractive">
          {`
            if ('serviceWorker' in navigator) {
              window.addEventListener('load', function () {
                navigator.serviceWorker.register('/sw.js').catch(function () {
                  // Falha de registro não deve quebrar a aplicação — offline é um bônus.
                });
              });
            }
          `}
        </Script>
      </body>
    </html>
  );
}
