FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Run development server with host flag to allow external connections
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
