# Local Testing — Volledige Setup

Test alles lokaal voordat je naar Vercel + HF Spaces gaat.

---

## 1. Website (Port 8000)

```bash
# Terminal 1: Start webserver voor presell site
cd output/presell_site

# Python builtin server
python -m http.server 8000

# OF: http-server (sneller, betere caching)
npm install -g http-server
http-server -p 8000 -c-1
```

Test in browser:
```
http://localhost:8000
http://localhost:8000/about.html
http://localhost:8000/disclaimer.html
http://localhost:8000/privacy-policy.html
http://localhost:8000/terms-of-service.html
http://localhost:8000/contact.html
```

---

## 2. Streamlit App (Port 8501)

### 2.1 Setup Environment
```bash
# Terminal 2: Zet environment variables
$env:ANTHROPIC_API_KEY = "sk-ant-..." # Je echte API key
$env:STREAMLIT_AUTH_ENABLED = "true"
$env:STREAMLIT_PASSWORD = "test123"

# Of maak .env.local:
cat > .env.local << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
STREAMLIT_AUTH_ENABLED=true
STREAMLIT_PASSWORD=test123
EOF

# Python laadt .env.local automatisch via python-dotenv
```

### 2.2 Run Streamlit
```bash
# Terminal 2: Start Streamlit app
cd c:\data\Claude\MaxWeb
streamlit run streamlit_simple.py

# Output:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
# Network URL: http://192.168.x.x:8501
```

### 2.3 Test Login
1. Ga naar `http://localhost:8501`
2. Zie login screen
3. Vul in: password = `test123`
4. Click **Login**
5. Je bent nu in de app!

---

## 3. Simuleer Subdomain (Optional)

Als je `domain.com:8000` en `app.domain.com:8501` lokaal wilt testen:

### Edit `C:\Windows\System32\drivers\etc\hosts`
```
127.0.0.1  domain.com
127.0.0.1  app.domain.com
```

Nu in browser:
```
http://domain.com:8000        → Website
http://app.domain.com:8501    → Streamlit (login → app)
```

---

## 4. Full Local Test Checklist

### Website (Port 8000)
- [ ] Homepage laadt
- [ ] Header navigation werkt (alle links)
- [ ] Articles grid toont 8 artikelen
- [ ] Footer correct
- [ ] CSS styled correct (kleuren, gradients)
- [ ] Responsive op mobiel (F12 → mobile view)

### Streamlit App (Port 8501)
- [ ] Login scherm toont
- [ ] Verkeerd password → "Incorrect password"
- [ ] Correct password → App laadt
- [ ] Tab 1 (Offers) → CSV upload werkt
- [ ] Tab 2 (VSL Detection) → URL input werkt
- [ ] Tab 3 (Competition) → Sources selecteren werkt
- [ ] Tab 4 (Creatives) → Generate werkt
- [ ] Tab 5 (Pre-sell) → Generate en preview werkt

### Cross-Site
- [ ] Website → presell page preview
- [ ] Links in presell pages → website/disclaimer/contact werken
- [ ] All pages have consistent header + footer

---

## 5. Debugging Tips

### Streamlit Auth Debug
```python
# Voeg toe aan streamlit_simple.py voor debugging
import streamlit as st

st.write(f"DEBUG: Auth enabled = {os.getenv('STREAMLIT_AUTH_ENABLED')}")
st.write(f"DEBUG: Password set = {bool(os.getenv('STREAMLIT_PASSWORD'))}")
```

### Website CSS Issues
```bash
# Check CSS loads
curl http://localhost:8000/css/style.css

# Browser DevTools (F12)
# Network tab → zie alle CSS/JS laden
```

### Streamlit Errors
```bash
# Run met debug logging
streamlit run streamlit_simple.py --logger.level=debug
```

---

## 6. Performance Test (Before Production)

```bash
# Test website load speed
curl -w "Total time: %{time_total}s\n" http://localhost:8000

# Test CSS caching
curl -I http://localhost:8000/css/style.css
# Zoek: Cache-Control header

# Test Streamlit response time
# (just load app + check browser console for timing)
```

---

## 7. Clean Up Before Deployment

```bash
# Zorg dat je .env NIET committed bent
git status
# Mag niet tonen: .env

# Zorg dat output/ genegeerd is
git check-ignore output/presell_site/index.html
# Moet output: output/presell_site/index.html

# Controleer requirements.txt compleet is
cat requirements.txt | wc -l
# Moet minimaal 12+ lines zijn
```

---

## 8. Final Verification Script

Maak `test_local.sh`:

```bash
#!/bin/bash

echo "=== Local MaxWeb Testing ==="
echo ""

# Check Python version
echo "[1] Python version:"
python --version

# Check venv
echo "[2] Virtual environment:"
if [ -d "venv" ]; then 
    echo "  ✓ venv exists"
else 
    echo "  ✗ venv missing (run: python -m venv venv)"
fi

# Check dependencies
echo "[3] Key packages:"
python -c "import streamlit; print('  ✓ streamlit')" 2>/dev/null || echo "  ✗ streamlit missing"
python -c "import anthropic; print('  ✓ anthropic')" 2>/dev/null || echo "  ✗ anthropic missing"
python -c "import pydantic; print('  ✓ pydantic')" 2>/dev/null || echo "  ✗ pydantic missing"

# Check env variables
echo "[4] Environment:"
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "  ⚠ ANTHROPIC_API_KEY not set"
else
    echo "  ✓ ANTHROPIC_API_KEY set (${#ANTHROPIC_API_KEY} chars)"
fi

# Check website files
echo "[5] Website files:"
[ -f "output/presell_site/index.html" ] && echo "  ✓ index.html" || echo "  ✗ index.html missing"
[ -f "output/presell_site/css/style.css" ] && echo "  ✓ style.css" || echo "  ✗ style.css missing"
[ -f "output/presell_site/disclaimer.html" ] && echo "  ✓ disclaimer.html" || echo "  ✗ disclaimer.html missing"

# Check Streamlit config
echo "[6] Streamlit config:"
[ -f ".streamlit/config.toml" ] && echo "  ✓ config.toml" || echo "  ✗ config.toml missing"

echo ""
echo "=== Ready to test! ==="
echo ""
echo "Terminal 1 (Website):"
echo "  cd output/presell_site && python -m http.server 8000"
echo ""
echo "Terminal 2 (Streamlit):"
echo "  streamlit run streamlit_simple.py"
echo ""
echo "Browser:"
echo "  Website:   http://localhost:8000"
echo "  Streamlit: http://localhost:8501"
```

Run:
```bash
chmod +x test_local.sh
./test_local.sh
```

---

## Volgorde: Local → Production

```
Local ✓  → Website on 8000, App on 8501
   ↓
Vercel → domain.com
HF Spaces → app.domain.com
   ↓
Production ✓
```

Alles lokaal getest? Dan kan je met vertrouwen deployen!
