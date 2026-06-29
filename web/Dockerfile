# ── Stage 1: build Angular app ────────────────────────────────────────────────
FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@11.9.0 --activate

WORKDIR /app

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts

COPY . .
RUN pnpm exec ng build --configuration=production

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:stable-alpine AS runtime

RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

COPY nginx.conf /etc/nginx/http.d/default.conf
COPY --from=builder /app/dist/web/browser /usr/share/nginx/html

USER nginx

EXPOSE 8080
