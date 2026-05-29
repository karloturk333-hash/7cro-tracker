# 7CRO Tracker — Tehnicki pregled & obrana odluka

> Sazetak za razgovor: zasto je projekt slozen ovako kako jest.
> Cilj nije nabubati napamet, nego razumjeti logiku iza svake odluke.

---

## Sto projekt radi (jedna recenica)
Dashboard koji prati InterCapital CROBEX10tr UCITS ETF (7CRO) sa
Zagrebacke burze — candlestick graf, volume, tehnicki indikatori
(SMA/EMA/RSI/MACD), s automatskim dnevnim osvjezavanjem podataka.

---

## Zasto CSV-first (a ne odmah live API)?
**Pouzdanost dema.** Aplikacija MORA raditi kad je netko otvori — na
razgovoru, na deployu, bilo kad. Ako bih ovisio iskljucivo o live API-ju,
demo bi pao u trenutku kad je API nedostupan ili nema podataka za 7CRO.
Zato:
- Ugradjeni CSV je uvijek dostupan -> app nikad ne pukne
- API/auto-update je nadogradnja povrh toga, ne ovisnost
- Fallback lanac: uploadani CSV -> auto-update CSV -> ugradjeni CSV

Princip: **graceful degradation** — ako jedan izvor zakaze, sljedeci
preuzme. Korisnik uvijek vidi podatke.

## Zasto cron (GitHub Actions) a ne live pull u aplikaciji?
Tri razloga:
1. **Radi i kad je app ugasen.** Cron commita podatke u repo neovisno o
   tome gleda li itko app. Live pull bi se dogodio samo kad netko otvori.
2. **ZSE API vraca intraday podatke dok je burza otvorena** — nezavrseni
   "pola-dana" candle. Cron je namjesten na 18h (nakon zatvaranja), pa
   uvijek povlaci zavrsen dnevni podatak. (Zato i postoji
   `drop_unfinished_today` zastita.)
3. **Manje opterecenje** — jedan poziv dnevno umjesto na svako otvaranje.

## Zasto modularna struktura (data / core / ui)?
Razdvajanje odgovornosti:
- `data/` — odakle podaci dolaze (loader, API, normalizacija)
- `core/` — cista logika (indikatori, statistike) — lako testirati
- `ui/` — prikaz (graf, kontrole)
Posljedica: kad sam htio dodati FastAPI/Next.js verziju, `core/` i `data/`
se reusaju netaknuti — samo se mijenja UI sloj. Cista granica = lak
prelazak.

## Zasto HRK->EUR konverzija?
7CRO je trgovao u HRK do 31.12.2022, u EUR od 1.1.2023. Bez konverzije,
graf bi imao lazni "skok" preko noci (cijena pada sa ~100 na ~13) sto je
samo promjena valute, ne vrijednosti. Konvertiram HRK dio fiksnim tecajem
(7,53450) da graf bude kontinuiran i financijski tocan.

## Zasto TDD (testovi prvo)?
Financijski podaci moraju biti tocni. Testovi:
- Hvataju regresije kad mijenjam kod
- Dokumentiraju ocekivano ponasanje (npr. "OTC redovi se filtriraju")
- Daju mi sigurnost da merge logika ne gubi/duplira podatke
42 testa pokrivaju loader, indikatore, statistike, API, merge.

## Sto je RSI / MACD (znam vec, kratko)
- **RSI** — momentum oscilator 0-100; >70 prekupljeno, <30 preprodano
- **MACD** — razlika dvije EMA (12/26) + signalna linija (9); histogram
  pokazuje momentum

## Iskreno o procesu
Koristio sam AI asistente kao ubrzanje pri pisanju koda. Tehnicke odluke
(arhitektura, izvori podataka, rjesavanje valutnog prijelaza, intraday
problem) su moje. Razumijem svaki dio koda i mogu objasniti zasto je tu.
To je nacin rada s modernim alatima — fokus na razumijevanju i vodjenju,
ne na pamcenju sintakse.

---

## Moguca pitanja & kratki odgovori
**"Sto bi promijenio?"** -> Drawing tools (trendline, Fibonacci) traze
prelazak s read-only wrappera na custom JS graf — to je u ROADMAP-u (v4,
FastAPI + Next.js).

**"Kako skaliras na vise instrumenata?"** -> Loader i API su vec
parametrizirani po ISIN-u; treba samo dropdown za izbor + usporedni overlay.

**"Sto ako ZSE promijeni format?"** -> Parsiranje je izolirano u jednoj
funkciji (`_read_zse_csv`); mijenja se samo ona, ostatak appa ostaje.
