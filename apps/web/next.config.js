/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Desabilita o cache persistente do webpack em disco (.next/cache/webpack).
  // Necessário porque este projeto vive numa pasta sincronizada por Google
  // Drive Desktop: o cache do webpack escreve muitos arquivos pequenos
  // rapidamente, e o cliente de sincronização derruba isso com
  // "EINVAL: invalid argument, write" (crasha o build inteiro — não é um bug
  // do Next.js). Sem persistência em disco, cada build recompila do zero
  // (mais lento), mas funciona de forma confiável. Ver docs/HISTORICO.md e
  // ~/.claude/rules/node-env.md.
  webpack: (config) => {
    config.cache = false;
    return config;
  },
};

module.exports = nextConfig;
