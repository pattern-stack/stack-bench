FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY app/frontend/package.json app/frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY app/frontend/ ./

# Build
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
