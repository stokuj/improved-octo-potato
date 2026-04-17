FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build-time environment variables
ARG PUBLIC_API_URL
ENV PUBLIC_API_URL=$PUBLIC_API_URL

RUN npm run build

FROM node:22-alpine

WORKDIR /app

COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build

EXPOSE 3000

# Run with node adapter
CMD ["node", "build"]
