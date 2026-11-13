# https://docs.docker.com/guides/reactjs/?utm_source=chatgpt.com#step-1-create-the-dockerfile

#step 1
ARG NODE_VERSION=24.12.0-alpine
ARG NGINX_VERSION=alpine3.22

FROM node:${NODE_VERSION} as builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache, target=/root/.npm npm ci

COPY . .
RUN npm run build

# step 2 
FROM nginxinc/nginx-unprivileged:${NGINX_VERSION} AS runner

COPY nginx.conf /etc/nginx/nginx.conf

COPY --chown=nginx:nginx --from=builder \ 
    /app/build /usr/share/nginx/html

USER nginx

EXPOSE 8080

ENTRYPOINT ["nginx", "-c", "/etc/nginx/nginx.conf"]
CMD ["-g", "daemon off;"]