# LEXIMASTER LIVE — internet orqali ishlaydigan versiya

Bu arxiv — internetga joylashtirish uchun tayyor **FastAPI veb-ilovasi**, hali ommaviy saytga yuklanmagan.

## Eng sodda yo'l: GitHub + Render

1. GitHub hisobingizga kiring va yangi **private** repository yarating.
2. Ushbu papkadagi fayllarni repository ildiziga yuklang (`server.py`, `words.json`, `static/`, `requirements.txt`, `render.yaml`). ZIP faylni bitta arxiv sifatida emas, ochilgan fayllarni yuklang.
3. Render.com hisobingizga kiring → **New** → **Blueprint** → GitHub repository'ni tanlang → **Apply**. `render.yaml` serverni sozlaydi.
4. Deploy yakunlangach, Render sizga `https://...onrender.com` ko'rinishidagi manzil beradi.
5. Kompyuterda shu HTTPS manzilni oching, musobaqa yarating. QR-kod internetdagi `/join/KOD` manzilini beradi; telefonlar istalgan internet tarmog'idan kira oladi.
6. Kompyuter va telefonlarda birgalikda sinov o'tkazing: kirish, boshlash, javob, reyting, yakunlash, qayta boshlash.

## MUHIM: bepul hosting cheklovi

Render'ning bepul xizmati diskdagi SQLite faylni doimiy saqlashni kafolatlamaydi. Restart, redeploy yoki uyqudan uyg'onish paytida musobaqa xonalari, ishtirokchilar va natijalar yo'qolishi mumkin. Bepul hosting demo/sinov uchun; haqiqiy musobaqa uchun **persistent diskli hosting** yoki **PostgreSQL** kerak. Bepul instansiya uxlab qolishi va uyg'onish vaqtida kechikish bo'lishi mumkin. Bu loyiha bir server jarayoni bilan ishlaydi; ko'p nusxaga masshtablash uchun ma'lumotlar bazasi va sinxronizatsiya arxitekturasi qayta ko'rilishi kerak.

## Doimiy ma'lumotlar uchun (pullik persistent diskli Render)

Render xizmatida persistent diskni `/var/data` ga ulang va `LEXIMASTER_DB=/var/data/leximaster.sqlite3` environment variable o'rnating. Bunday disk bepul tarifda mavjud bo'lmasligi mumkin. Disk ulashdan oldin ma'lumotlar zaxira nusxasi siyosatini ishlab chiqing.

## Maxfiylik va xavfsizlik

- Ishtirokchilar ism bilan kiradi; shaxsiy ma'lumotlarni kiritmang.
- O'qituvchi sessiya kalitini begonalarga bermang.
- Ochiq internetda yaratish/join endpointlarida rate-limit va admin login yo'q: katta ommaviy tadbir uchun qo'shimcha xavfsizlik zarur.
- PDFdan ajratilgan 4 111 ta lug'at yozuvi hali to'liq muharrirlik tekshiruvidan o'tmagan.

## Lokal sinov

`python -m pip install -r requirements.txt`
`python -m uvicorn server:app --host 127.0.0.1 --port 8000`
`http://localhost:8000`
