# 7CRO Platform — Roadmap

## Trenutno stanje (v3, Streamlit MVP) ✅
Funkcionalan, deployan dashboard:
- Candlestick + volume + SMA/EMA/RSI/MACD
- HRK→EUR konverzija, hover legenda, fullscreen
- Auto-pull sa ZSE REST API (GitHub Actions cron, radnim danom 18h)
- 37 testova (TDD), modularna arhitektura (data / core / ui razdvojeni)

Ovo je verzija za prijavu — radi, deployana, pokazuje cijeli ciklus.

---

## Full verzija (v4) — FastAPI backend + Next.js frontend

### Zašto
- Streamlit je read-only za graf → nema pravih drawing toolova (trendline,
  Fibonacci, ravnalo mišem). Next.js + lightweight-charts to rješava nativno.
- React/Next.js za clean UI/UX i brzinu; Python ostaje za podatke/analitiku.
- Pokazuje full-stack: Python data engineering + moderni frontend.

### Što se REUSEA (ništa se ne baca)
- `core/` (indicators, stats) i `data/` (loaders, zse_api, merge) → postaju
  FastAPI servisni sloj, skoro netaknuti
- Svih 37 testova ostaje validno
- GitHub Actions cron + `scripts/fetch_zse.py` → reuse 1:1 (neovisan o frontendu)

### Ciljana arhitektura (monorepo)
```
7cro-platform/
├── backend/          # FastAPI
│   ├── core/         # (iz Streamlit projekta) indicators, stats
│   ├── data/         # (iz Streamlit projekta) loaders, zse_api
│   ├── routes/       # NOVO: API endpointi
│   ├── main.py       # FastAPI app
│   └── tests/        # (iz Streamlit projekta) + novi route testovi
├── frontend/         # Next.js + TypeScript
│   ├── components/   # Chart, Toolbar, IndicatorPanel, DrawingTools
│   ├── lib/          # fetch wrapper za backend
│   └── app/          # Next.js app router
└── .github/workflows/  # cron pipeline (reuse)
```

### API endpointi (skica)
```
GET /api/ohlcv?period=1y                  → candlestick + volume JSON
GET /api/indicators?sma=20&ema=50&rsi=14  → indikatorske serije
GET /api/stats                            → zadnja cijena, 52w, %change
GET /api/health                           → status + zadnji datum podataka
```

### Frontend funkcionalnosti (ono što Streamlit ne moze)
- **Drawing tools**: trendline, horizontalna linija, Fibonacci retracement,
  ravnalo (measure) — sve mišem preko lightweight-charts plugina
- Crteži spremljeni u localStorage (preživljavaju refresh)
- Pravi fullscreen, custom hover tooltip uz kursor
- Usporedba više instrumenata (7CRO vs CROBEX) — overlay normaliziran na 100

### Redoslijed izvedbe v4
1. FastAPI skeleton + prebaci core/ i data/ → izloži /api/ohlcv (TDD)
2. Next.js skeleton + lightweight-charts, povuci /api/ohlcv, nacrtaj candlestick
3. Indikatori (toggle UI → /api/indicators)
4. Drawing tools (trendline → Fib → ravnalo)
5. Deploy: backend (Railway/Render), frontend (Vercel)

### TDD princip (nastaviti)
Svaka nova funkcija: prvo test, pa implementacija. Backend rute testirati
s FastAPI TestClient; frontend komponente s React Testing Library.

---

## Prioritet
Završi i pošalji Streamlit MVP PRIJE nego kreneš v4.
v4 je "evo na čemu trenutno radim" — pokazuje i isporuku i ambiciju.
