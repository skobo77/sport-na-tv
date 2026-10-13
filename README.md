# Sport na TV

Dnevni raspored sportskih prijenosa na hrvatskim kanalima (Arena Sport, Sportklub, HRT, MAX Sport…). Raspored se osvježava sam, svako jutro i u podne.

## Kako radi

- `index.html` je stranica. Čita `data/schedule.json`.
- `scraper/scrape.py` dohvaća raspored za danas i iduća dva dana sa sporter.com.hr i zapisuje `data/schedule.json`.
- `.github/workflows/update.yml` pokreće skriptu automatski u 6:00 i 13:00 (ljeti) i sprema novi raspored u repozitorij. GitHub Pages zatim objavi novu verziju.

Ako dohvat ne uspije, stari raspored ostaje, a GitHub ti pošalje mail da zadatak nije prošao.

## Postavljanje (jednom, ~10 minuta)

1. **Novi repozitorij.** Na GitHubu klikni *New repository*, nazovi ga npr. `sport-na-tv` i ostavi ga **Public** (GitHub Pages na besplatnom računu radi samo za javne repozitorije).
2. **Učitaj datoteke.** Na stranici repozitorija odaberi *Add file → Upload files* i povuci sve iz raspakirane mape.
   Mapa `.github` je skrivena (počinje točkom) i pri povlačenju se često ne učita. Ako je nakon uploada nema u repozitoriju: *Add file → Create new file*, za ime upiši `.github/workflows/update.yml`, zalijepi sadržaj te datoteke i spremi.
3. **Dozvoli zapisivanje.** *Settings → Actions → General → Workflow permissions →* **Read and write permissions** → *Save*.
4. **Uključi stranicu.** *Settings → Pages → Source: Deploy from a branch*, branch **main**, mapa **/ (root)** → *Save*. Za minutu-dvije stranica je na `https://TVOJE-IME.github.io/sport-na-tv/`.
5. **Prvo pokretanje.** *Actions → Osvježi raspored → Run workflow*. Kad se pojavi zelena kvačica, u `data/schedule.json` je svježi raspored.

## Ako nešto ne radi

- **Zadatak u Actions je crven.** Otvori ga i pogledaj ispis koraka *Dohvati raspored*. Najčešći uzrok je da je sporter.com.hr promijenio izgled stranice, pa parser treba prilagoditi.
- **Zakazani zadaci su stali.** GitHub pauzira zakazane zadatke u repozitorijima koji dugo nemaju aktivnosti. U kartici *Actions* ih samo ponovno uključiš.
- **Stranica lokalno javlja grešku.** Otvaranje `index.html` dvoklikom ne radi jer preglednik tada ne smije čitati JSON. U mapi projekta pokreni `python -m http.server` i otvori `http://localhost:8000`.

## Lokalno pokretanje skripte

```
pip install requests beautifulsoup4
python scraper/scrape.py
```

## Napomena o izvoru podataka

Raspored se preuzima sa sporter.com.hr, dvaput dnevno, s jasno označenim User-Agentom. Ako stranicu misliš javno dijeliti, javi im se i pitaj smiju li se njihovi podaci koristiti na ovaj način.
