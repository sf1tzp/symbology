FROM node:24-alpine AS builder

WORKDIR /app

# Build arguments for environment configuration
ARG ENVIRONMENT=production
ARG SYMBOLOGY_API_HOST=localhost
ARG SYMBOLOGY_API_PORT=8000
ARG LOG_LEVEL=info

# Set environment variables for Vite build
ENV ENVIRONMENT=${ENVIRONMENT}
ENV SYMBOLOGY_API_HOST=${SYMBOLOGY_API_HOST}
ENV SYMBOLOGY_API_PORT=${SYMBOLOGY_API_PORT}
ENV LOG_LEVEL=${LOG_LEVEL}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the SvelteKit application with environment variables
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets to nginx
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
