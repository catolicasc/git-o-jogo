FROM node:22
WORKDIR /app

# Copiar arquivos de dependência
COPY git-o-jogo/package*.json ./

# Instalar dependências
RUN npm install

# Copiar resto do código
COPY git-o-jogo/ .

# Buildar aplicação
RUN npm run build

# Expor a porta que o app usa (geralmente 3000)
EXPOSE 3000

CMD ["npm", "start"]