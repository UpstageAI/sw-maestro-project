FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY FE/package.json ./FE/
RUN npm ci --workspace FE

COPY FE/ ./FE/

WORKDIR /app/FE
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]
