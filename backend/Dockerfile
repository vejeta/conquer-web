# SPDX-FileCopyrightText: 2025 Juan Manuel Méndez Rey
# SPDX-License-Identifier: GPL-3.0-or-later

FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --production

# Copy application files
COPY src/ ./src/
COPY ../frontend/ ../frontend/

# Create database directory
RUN mkdir -p db

# Expose port
EXPOSE 3000

# Start server
CMD ["npm", "start"]
