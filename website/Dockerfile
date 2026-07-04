FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Templated config: nginx:alpine runs envsubst on /etc/nginx/templates/*.template at startup,
# substituting only the env vars we define (BACKEND_INTERNAL_URL). nginx runtime vars like
# $host / $remote_addr are left untouched because no matching env vars exist.
COPY nginx.conf /etc/nginx/templates/default.conf.template
# Default keeps docker-compose working (resolves the `backend` service); ACA overrides this
# with the backend's internal FQDN.
ENV BACKEND_INTERNAL_URL=http://backend:5000
ENV NGINX_ENVSUBST_TEMPLATE_SUFFIX=.template
ENV NGINX_ENVSUBST_FILTER=BACKEND_INTERNAL_URL
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
