FROM node:22.12-alpine AS builder

WORKDIR /app

COPY src/filesystem/package.json /app/package.json
COPY src/filesystem/tsconfig.json /app/tsconfig.json
COPY src/filesystem/src /app/src
COPY tsconfig.json /tsconfig.json

RUN --mount=type=cache,target=/root/.npm npm install
RUN npm run build


FROM node:22-alpine AS release

WORKDIR /app

COPY --from=builder /app/dist /app/dist
COPY --from=builder /app/package.json /app/package.json
COPY --from=builder /app/package-lock.json /app/package-lock.json

ENV NODE_ENV=production

RUN npm ci --ignore-scripts --omit-dev

ENTRYPOINT ["node", "/app/dist/index.js"]
