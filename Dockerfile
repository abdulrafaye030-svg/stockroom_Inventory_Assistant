# Stage 1: build the React frontend into dist/
FROM node:22-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

# Stage 2: run the Python server, which serves dist/ and the /api endpoints
FROM python:3.12-slim
WORKDIR /app
COPY server.py chatbot.py database.py auth.py envfile.py ./
COPY --from=frontend /app/dist ./dist
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
# Hosting platforms such as Render set PORT; listen on all interfaces so it is reachable.
CMD ["sh", "-c", "python server.py --host 0.0.0.0 --port ${PORT:-8000}"]
