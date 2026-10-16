FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173
# Dev server (HMR) — fine for this demo platform.
CMD ["npm", "run", "dev"]
