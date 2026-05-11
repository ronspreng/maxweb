# MaxWeb System — Deployment Guide (Vercel + HF Spaces)

## Overview

```
domain.com          → Vercel (Statische presell website)
app.domain.com      → Hugging Face Spaces (Streamlit app met auth)
```

---

## 1. Website Deployment (Vercel)

### 1.1 Vercel Account Setup
1. Ga naar https://vercel.com en maak account aan (gratis)
2. Link je GitHub account (of gebruik email)

### 1.2 Deploy Website
```bash
# Installeer Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy presell_site folder
cd output/presell_site
vercel deploy --prod

# Je krijgt URL: https://presell-site-xxx.vercel.app
```

### 1.3 Custom Domain (Vercel)
1. Ga naar https://vercel.com/dashboard
2. Selecteer je project
3. **Settings → Domains**
4. Voeg `domain.com` toe (je hebt DNS access nodig)

### 1.4 DNS Setup
Bij je registrar (GoDaddy, Namecheap, etc.):
```
Type: A
Name: @
Value: 76.76.19.21  (Vercel IP)
```
Na ~5 min: `domain.com` werkt!

---

## 2. Streamlit Deployment (Hugging Face Spaces)

### 2.1 HF Account Setup
1. Ga naar https://huggingface.co en maak account aan (gratis)
2. Ga naar https://huggingface.co/spaces/create
3. Kies:
   - **Owner:** je username
   - **Space name:** `maxweb-app`
   - **License:** Open RAIL-M
   - **Select the Space SDK:** `Docker`
   - **Visibility:** Private (!)

### 2.2 Repository Setup
```bash
# Clone HF Space repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/maxweb-app
cd maxweb-app

# Kopieer projectbestanden
cp -r /path/to/maxweb/* .

# Zorg ervoor dat je hebt:
# - streamlit_simple.py
# - requirements.txt
# - src/ folder (modules)
# - .env (NIET committen!)
```

### 2.3 Dockerfile voor HF Spaces
```bash
# Maak Dockerfile aan
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Expose port
EXPOSE 7860

# Run Streamlit
CMD ["streamlit", "run", "streamlit_simple.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0"]
EOF
```

### 2.4 Environment Variables (HF Spaces)
1. Ga naar **Space Settings → Repository secrets**
2. Voeg deze toe:

```
ANTHROPIC_API_KEY=sk-ant-...     (je Claude API key)
STREAMLIT_AUTH_ENABLED=true
STREAMLIT_PASSWORD=super_secret_password_123
```

### 2.5 Commit & Deploy
```bash
git add .
git commit -m "Initial MaxWeb app deployment"
git push

# HF Spaces bouwt automatisch (2-3 min)
# Je krijgt URL: https://huggingface.co/spaces/YOUR_USERNAME/maxweb-app
```

---

## 3. DNS Subdomain Setup

Bij je registrar: voeg CNAME record toe voor `app.domain.com`:

```
Type: CNAME
Name: app
Value: huggingface.space (of je HF Space custom domain, zie stap 3.1)
```

### 3.1 HF Spaces Custom Domain
1. In je HF Space → **Settings → Custom URL**
2. Voeg `app.domain.com` toe
3. HF geeft je een CNAME target → voeg toe bij registrar

---

## 4. Verification Checklist

```
[ ] Website live op domain.com
    curl https://domain.com
    → Zie index.html presell site

[ ] Streamlit app live op app.domain.com
    → Zie login screen
    → Vul password in

[ ] SSL certificaten automatisch (Vercel + HF)

[ ] API keys beveiligd in environment variables
    → ANTHROPIC_API_KEY enkel op HF Spaces
    → STREAMLIT_PASSWORD enkel op HF Spaces

[ ] Website links naar app.domain.com werken
    (future: voeg "Open App" knop toe aan index.html)
```

---

## 5. Updates & Maintenance

### Update Website (Vercel)
```bash
# Maak changes
nano output/presell_site/index.html

# Redeploy
cd output/presell_site
vercel deploy --prod
```

### Update Streamlit App (HF Spaces)
```bash
# Clone HF repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/maxweb-app

# Voeg changes toe
git add .
git commit -m "Update: add new feature"
git push

# HF bouwt automatisch opnieuw
```

---

## 6. Security Best Practices

✓ **Environment Variables:** Nooit in code!  
✓ **GitHub:** Voeg `.env` toe aan `.gitignore`  
✓ **HF Secrets:** Alleen op HF Spaces instellen  
✓ **SSL:** Automatisch (Vercel + HF)  
✓ **Password:** Wijzig `STREAMLIT_PASSWORD` na deployment!  

---

## 7. Cost Estimate

| Service | Tier | Cost/maand | Notes |
|---------|------|-----------|-------|
| Vercel | Hobby | $0 | Website statisch, gratis |
| HF Spaces | Free | $0 | CPU instances, gratis |
| Domain | Namecheap | ~$10 | Je eigen keus |
| **Total** | | **~$10** | Schaal naar betaald alleen als nodig |

---

## Troubleshooting

### Streamlit app laadt niet
```bash
# Check HF Space logs
# Settings → Activity logs

# Lokaal testen
streamlit run streamlit_simple.py --logger.level=debug
```

### Domain niet resolving
```bash
# Check DNS propagatie
nslookup domain.com
nslookup app.domain.com

# Wacht 5-15 minuten na DNS changes
```

### API key error
```bash
# Zet API key in HF Spaces Secrets, NOT in .env file
# Test lokaal eerst:
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run streamlit_simple.py
```

---

## Summary

```bash
# Website
1. vercel deploy output/presell_site/
2. DNS: @ A record → Vercel
3. Vercel: add custom domain domain.com

# App
1. Create HF Space (maxweb-app)
2. Push code + Dockerfile
3. Add secrets: ANTHROPIC_API_KEY, STREAMLIT_PASSWORD
4. DNS: app CNAME → HF Space

# Timing
Website live: 5 min
App live: 10 min
DNS resolving: 5-15 min

Done! 🚀
```
