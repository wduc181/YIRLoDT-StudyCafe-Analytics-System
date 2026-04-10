FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Expose dev server port
EXPOSE 5173

# Run Vite dev server — bind to all interfaces for Docker
CMD ["npm", "run", "dev", "--", "--host"]
