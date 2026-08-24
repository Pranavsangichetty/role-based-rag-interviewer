# Stage 1: Build dependencies & production bundle
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests
COPY package.json package-lock.json ./

# Install all dependencies for build
RUN npm ci

# Copy application source
COPY app/ ./app/
COPY tsconfig.json next-env.d.ts ./

# Accept API URL build argument
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production

# Build Next.js application
RUN npm run build

# Stage 2: Production runner
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000

# Copy package manifests and production dependencies
COPY package.json package-lock.json ./
RUN npm ci --only=production

# Copy built application assets from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/app ./app

EXPOSE 3000

CMD ["npm", "run", "start"]
