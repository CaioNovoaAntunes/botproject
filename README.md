# AutoPost — Publicador Multiplataforma

Publique vídeos no **Facebook**, **Instagram** e **TikTok** simultaneamente com um único upload.

## Funcionalidades

- Upload de vídeo MP4, MOV, AVI, MKV ou WEBM
- Publicação simultânea em Facebook, Instagram e TikTok
- Suporte a título, descrição e tags
- Histórico de publicações
- Configuração via interface web
- OAuth integrado para TikTok

## Como usar

### 1. Instalar

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e preencha:

```bash
cp .env.example .env
```

Ou acesse `http://localhost:5000/setup` após iniciar o servidor.

### 3. Rodar

```bash
python app.py
```

Acesse **http://localhost:5000**

### 4. Configurar cada plataforma

#### Facebook
1. Crie um App em https://developers.facebook.com/apps/
2. Adicione "Facebook Login" e "Graph API"
3. Gere um Access Token de Página
4. Copie o Page ID da sua página do Facebook

#### Instagram
1. Use uma Conta Comercial ou de Criador no Instagram
2. Conecte-a a uma Página do Facebook
3. Gere um token com escopos `instagram_basic`, `instagram_content_publish`, `pages_show_list`

#### TikTok
1. Crie um App em https://developers.tiktok.com/apps/
2. Ative "Content Posting API"
3. Configure Redirect URL como `http://localhost:5000/auth/tiktok/callback`
4. No `/setup`, clique em "Conectar com TikTok" para autorizar

### 5. Publicar

- Selecione o vídeo, preencha título/descrição/tags
- Escolha as plataformas
- Clique em **Publicar Agora**

## Deploy no Render

1. Conecte seu repositório GitHub ao Render
2. Crie um **Web Service**
3. **Start Command**: `gunicorn app:app`
4. Configure as variáveis de ambiente (as mesmas do `.env`) nos **Environment Variables** do Render

OBS: Para usar `PULL_FROM_URL` no TikTok, o domínio precisa ser verificado em *developers.tiktok.com > URL Properties*. Em ambiente local, o sistema usa `FILE_UPLOAD` automaticamente.

## Tecnologias

- Python + Flask
- TikTok Content Posting API
- Facebook Graph API
- Instagram Graph API
