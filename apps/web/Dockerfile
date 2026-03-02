FROM node:25-alpine AS base
WORKDIR /app

# Install deps
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source
COPY . .

# Dev command (overridden in docker-compose)
EXPOSE 3000
CMD ["npm", "run", "dev"]
