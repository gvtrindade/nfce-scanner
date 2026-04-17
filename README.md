# nfce-scanner

Parse Brazilian NFC-e (Nota Fiscal Eletrônica do Consumidor) HTML invoices into structured JSON.

## Install

```bash
uv install
```

Requires: libasound2t64, libgtk-3-0 (Ubuntu)

## Usage

```bash
uv run main.py <url>
```

Output: `result.json`

## What it extracts

- **seller**: name, CNPJ, address
- **items**: name, code, quantity, unit, unit_price, total_price
- **summary**: total_items, total_amount, discounts, total_payable
- **payments**: method, amount
- **consumer**: CPF or "not_identified"
- **invoice**: number, series, emission_datetime, access_key, protocol
- **taxes**: federal, estadual, municipal (optional)

## Tech

- BeautifulSoup4 — HTML parsing
- Camoufox — headless Firefox for dynamic content
