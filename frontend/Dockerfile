# Multi-stage build: Node builds the static Vite bundle, nginx serves it.
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# No VITE_API_URL is set here on purpose: the app then defaults to same-origin
# "/api" (see src/api.js), which is what the nginx reverse proxy expects.
RUN npm run build

FROM nginx:alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s \
    CMD wget -qO- http://localhost:80/ >/dev/null || exit 1
