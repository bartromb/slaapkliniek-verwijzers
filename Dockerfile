# Build-stage: rendert de pagina's; runtime-stage: alleen nginx en statische bestanden (geen Python).
FROM python:3.11-slim AS build
WORKDIR /src
COPY . .
RUN pip install --no-cache-dir "jinja2>=3.1" && python build.py

FROM nginx:alpine
COPY --from=build /src/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY nginx/security-headers.conf /etc/nginx/conf.d/security-headers.inc
