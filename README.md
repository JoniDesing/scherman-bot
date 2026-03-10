# 🤖 SCHERMAN BOT

Sistema de trading inteligente con datos reales de BYMA.

## Stack
- **Backend**: Python + Flask → Railway (gratis)
- **Frontend**: HTML/JS → GitHub Pages (gratis)
- **Datos**: Open BYMA Data (20 min delay, gratuito)

---

## Deploy en 10 pasos

### 1. Instalar Git
https://git-scm.com/download/win → instalar con opciones default

### 2. Crear repositorio en GitHub
- Entrá a github.com → "New repository"
- Nombre: `scherman-bot`
- Público ✓ → Create repository

### 3. Subir archivos (desde esta carpeta)
```bash
git init
git add .
git commit -m "Initial commit - Scherman Bot"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/scherman-bot.git
git push -u origin main
```

### 4. Activar GitHub Pages (frontend)
- En GitHub → Settings → Pages
- Source: Deploy from branch → main → / (root)
- Guardar → tu frontend estará en:
  `https://TU_USUARIO.github.io/scherman-bot`

### 5. Deploy backend en Railway
- Entrá a railway.app → New Project
- "Deploy from GitHub repo" → seleccioná `scherman-bot`
- Railway detecta automáticamente Python y usa el `Procfile`
- En 2-3 minutos tenés la URL del backend, algo como:
  `https://scherman-bot-production.up.railway.app`

### 6. Conectar frontend con backend
- Abrí tu GitHub Pages URL
- En el banner amarillo pegá la URL de Railway
- Click "Guardar y Conectar"
- ¡Listo! Datos reales de BYMA fluyendo.

---

## Archivos del proyecto
```
scherman-bot/
├── server.py          # Backend Flask - consulta BYMA
├── requirements.txt   # Dependencias Python
├── railway.toml       # Config Railway
├── Procfile           # Comando de inicio
├── index.html         # Frontend completo
└── README.md          # Este archivo
```

## Endpoints del backend
- `GET /api/cotizaciones` → CEDEARs y acciones en tiempo real
- `GET /api/bonos` → Bonos soberanos
- `GET /api/health` → Estado del servidor
- `GET /api/all` → Todo junto

## Notas importantes
- Open BYMA Data tiene 20 minutos de delay (suficiente para inversión, no para day trading)
- Railway plan gratuito: 500hs/mes (más que suficiente)
- GitHub Pages: ilimitado y gratuito
- El portfolio se guarda en el navegador (localStorage)
