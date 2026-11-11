FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/next.config.js ./
COPY --from=build /app/package.json ./
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
RUN npm install --omit=dev
# Menor privilégio (Trivy DS-0002): Next.js só lê arquivos em runtime.
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
