FROM node:18

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

EXPOSE 5173

CMD ["npx", "serve", "-s", "dist", "-l", "5173"]
