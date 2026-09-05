# ---- Build stage ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Stage 2 fix: Vite inlines import.meta.env.VITE_* values at BUILD time,
# when bundling. Setting VITE_API_BASE_URL as a container *runtime*
# environment variable (the previous approach) has no effect on an
# already-built app — it must be passed as a build ARG instead.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- Serve stage ----
# Stage 2 fix: previously this container ran the Vite *dev* server
# (npm run dev), which is not intended for anything beyond local editing.
# This stage serves the real production build instead.
FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/dist ./dist
EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
