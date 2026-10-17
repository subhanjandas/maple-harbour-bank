FROM node:24-bookworm-slim AS build
WORKDIR /source/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY architecture/ ../architecture/
RUN npm run build
FROM nginxinc/nginx-unprivileged:1.28.2-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /source/web/dist /usr/share/nginx/html
EXPOSE 8080
