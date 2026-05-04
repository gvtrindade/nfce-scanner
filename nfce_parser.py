import re
from collections import OrderedDict

from bs4 import BeautifulSoup


def parse_price(text: str) -> float:
    """Convert Brazilian price format (1.234,56) to float."""
    text = text.strip()
    text = text.replace(".", "").replace(",", ".")
    return float(text)


def parse_quantity(text: str) -> float:
    """Parse quantity which uses dot as decimal separator (e.g. 1.0000, 0.3750)."""
    return float(text.strip())


def parse_address(raw: str) -> dict:
    """Parse comma-separated address string into structured fields.

    Format: street, number, [complement], neighborhood, city, state
    The street portion may itself contain commas, so we anchor from the end:
    last=state, second-to-last=city, third-to-last=neighborhood,
    fourth-to-last=complement_or_number, remainder=street.
    """
    parts = [p.strip() for p in raw.split(",")]

    addr = OrderedDict()
    if len(parts) < 3:
        if parts:
            addr["street"] = ", ".join(parts)
        return addr

    state = parts[-1]
    city = parts[-2]
    neighborhood = parts[-3]
    remaining = parts[:-3]

    # remaining can be: [street, number, complement] or more if street had commas
    # Heuristic: last of remaining = complement (if >2), second-to-last = number,
    # everything before = street
    if len(remaining) >= 3:
        complement = remaining[-1]
        number = remaining[-2]
        street = ", ".join(remaining[:-2])
    elif len(remaining) == 2:
        number = remaining[-1]
        street = remaining[0]
        complement = ""
    else:
        street = remaining[0]
        number = ""
        complement = ""

    if street:
        addr["street"] = street
    if number:
        addr["number"] = number
    if complement:
        addr["complement"] = complement
    if neighborhood:
        addr["neighborhood"] = neighborhood
    if city:
        addr["city"] = city
    if state:
        addr["state"] = state
    return addr


def parse_seller(header) -> dict:
    """Extract seller info from accordion1 card-header."""
    divs = header.find_all("div", recursive=False)
    name = divs[0].get_text(strip=True) if divs else ""

    cnpj = ""
    address_raw = ""
    for div in divs:
        text = div.get_text()
        if "CNPJ:" in text:
            cnpj = text.replace("CNPJ:", "").strip()
        elif "," in text and "CNPJ:" not in text:
            address_raw = text.strip()

    return OrderedDict(
        [
            ("name", name),
            ("cnpj", cnpj),
            ("address", parse_address(address_raw)),
        ]
    )


def parse_items(collapse) -> list:
    """Extract and group items from collapse1."""
    items_map = OrderedDict()
    item_lis = collapse.select("ul:first-of-type > li.list-group-item")

    for li in item_lis:
        rows = li.find_all("div", class_="row")
        if len(rows) < 2:
            continue

        # First row: name + code
        name_tag = rows[0].find("p", class_="h6")
        if not name_tag:
            continue
        small = name_tag.find("small")
        code = ""
        if small:
            code_match = re.search(r"Cód:\s*(\d+)", small.get_text())
            if code_match:
                code = code_match.group(1)
            small.decompose()
        name = name_tag.get_text(strip=True)

        # Second row: quantity, unit, unit_price, total_price
        detail_text = rows[1].get_text()

        qty_match = re.search(r"Qtde\.:\s*([\d.]+)", detail_text)
        quantity = parse_quantity(qty_match.group(1)) if qty_match else 0.0

        unit_match = re.search(r"UN:\s*(\S+)", detail_text)
        unit = unit_match.group(1) if unit_match else ""

        uprice_match = re.search(r"Vl\. Unit\.:\s*([\d.,]+)", detail_text)
        unit_price = parse_price(uprice_match.group(1)) if uprice_match else 0.0

        # Total price from the col-3 span
        total_span = rows[1].find("div", class_="col-3")
        total_price = 0.0
        if total_span:
            total_price = parse_price(total_span.get_text(strip=True))

        key = (name, code, unit_price)
        if key in items_map:
            items_map[key]["count"] += 1
            items_map[key]["total_price"] += total_price
        else:
            items_map[key] = OrderedDict(
                [
                    ("name", name),
                    ("code", code),
                    ("quantity", quantity),
                    ("unit", unit),
                    ("unit_price", unit_price),
                    ("total_price", total_price),
                    ("count", 1),
                ]
            )

    return list(items_map.values())


def parse_summary(collapse) -> dict:
    """Extract summary totals from collapse1 bottom sections."""
    summary = OrderedDict()
    all_text = collapse.get_text()

    total_items_match = re.search(r"Qtd\. total de itens:\s*(\d+)", all_text)
    if total_items_match:
        summary["total_items"] = int(total_items_match.group(1))

    total_amount_match = re.search(r"Valor total R\$:\s*([\d.,]+)", all_text)
    if total_amount_match:
        summary["total_amount"] = parse_price(total_amount_match.group(1))

    discounts_match = re.search(r"Descontos R\$:\s*([\d.,]+)", all_text)
    if discounts_match:
        summary["discounts"] = parse_price(discounts_match.group(1))

    payable_match = re.search(r"Valor a pagar R\$:\s*([\d.,]+)", all_text)
    if payable_match:
        summary["total_payable"] = parse_price(payable_match.group(1))

    return summary


def parse_payments(collapse) -> list:
    """Extract payment info from collapse1."""
    payments = []
    all_text = collapse.get_text()

    # Find payment rows: method name followed by amount
    # The pattern is "Forma de pagamento:" header then rows of method + amount
    payment_section = re.search(
        r"Forma de pagamento:.*?Valor pago R\$:\s*(.*?)(?:Informação|Qtd\.|$)",
        all_text,
        re.DOTALL,
    )
    if not payment_section:
        return payments

    section_text = payment_section.group(1)
    # Find pairs: payment method and amount
    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    # Filter out the header lines
    method = None
    for line in lines:
        price_match = re.fullmatch(r"[\d.,]+", line)
        if price_match and method:
            payments.append(
                OrderedDict(
                    [
                        ("method", method),
                        ("amount", parse_price(line)),
                    ]
                )
            )
            method = None
        elif not price_match and "Valor pago" not in line:
            method = line

    return payments


def parse_consumer(accordion2) -> dict | str:
    """Extract consumer info from accordion2."""
    text = accordion2.get_text()
    if "não identificado" in text.lower():
        return "not_identified"

    cpf_match = re.search(r"CPF:\s*([\d.\-]+)", text)
    if cpf_match:
        return OrderedDict([("cpf", cpf_match.group(1))])

    return "not_identified"


def parse_access_key(accordion3) -> str:
    """Extract access key from accordion3."""
    text = accordion3.get_text()
    key_match = re.search(r"Chave de acesso:\s*([\d\s]+)", text)
    if key_match:
        return key_match.group(1).replace(" ", "").strip()
    return ""


def parse_invoice(accordion6) -> dict:
    """Extract invoice metadata from accordion6."""
    text = accordion6.get_text()
    invoice = OrderedDict()

    if "CONTINGÊNCIA" in text:
        invoice["emission_type"] = "contingencia"
    else:
        invoice["emission_type"] = "normal"

    num_match = re.search(r"Número:\s*(\d+)", text)
    if num_match:
        invoice["number"] = int(num_match.group(1))

    series_match = re.search(r"Série:\s*(\d+)", text)
    if series_match:
        invoice["series"] = int(series_match.group(1))

    emission_match = re.search(
        r"Emissão:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", text
    )
    if emission_match:
        invoice["emission_datetime"] = emission_match.group(1)

    protocol_match = re.search(
        r"Protocolo de Autorização:\s*(\d+)\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})",
        text,
    )
    if protocol_match:
        invoice["protocol"] = protocol_match.group(1)
        invoice["protocol_datetime"] = protocol_match.group(2)

    return invoice


def parse_taxes(accordion4) -> dict | None:
    """Extract tax breakdown from accordion4 if present."""
    if accordion4 is None:
        return None

    text = accordion4.get_text()
    taxes = OrderedDict()

    federal_match = re.search(r"FEDERAL R\$?\s*([\d.,]+)", text)
    if federal_match:
        taxes["federal"] = parse_price(federal_match.group(1))

    estadual_match = re.search(r"ESTADUAL R\$?\s*([\d.,]+)", text)
    if estadual_match:
        taxes["estadual"] = parse_price(estadual_match.group(1))

    municipal_match = re.search(r"MUNICIPAL R\$?\s*([\d.,]+)", text)
    if municipal_match:
        taxes["municipal"] = parse_price(municipal_match.group(1))

    coo_match = re.search(r"COO:\s*(\d+)", text)
    if coo_match:
        taxes["coo"] = int(coo_match.group(1))

    pdv_match = re.search(r"PDV:\s*(\d+)", text)
    if pdv_match:
        taxes["pdv"] = int(pdv_match.group(1))

    # Also check for single tax line (example.html format)
    single_tax_match = re.search(
        r"Lei Federal 12\.741/2012\)?\s*R\$:\s*([\d.,]+)", text
    )
    if single_tax_match and not taxes:
        taxes["total"] = parse_price(single_tax_match.group(1))

    return taxes if taxes else None


def parse_taxes_from_summary(collapse) -> dict | None:
    """Extract single tax line from summary section (example.html format)."""
    text = collapse.get_text()
    tax_match = re.search(r"Lei Federal 12\.741/2012\)\s*R\$:\s*([\d.,]+)", text)
    if tax_match:
        return OrderedDict([("total", parse_price(tax_match.group(1)))])

    # Also try the accordion4-style inline format
    federal_match = re.search(r"FEDERAL R\$?\s*([\d.,]+)", text)
    if federal_match:
        taxes = OrderedDict()
        taxes["federal"] = parse_price(federal_match.group(1))
        estadual_match = re.search(r"ESTADUAL R\$?\s*([\d.,]+)", text)
        if estadual_match:
            taxes["estadual"] = parse_price(estadual_match.group(1))
        municipal_match = re.search(r"MUNICIPAL R\$?\s*([\d.,]+)", text)
        if municipal_match:
            taxes["municipal"] = parse_price(municipal_match.group(1))
        return taxes

    return None


def parse_nfce(html: str) -> dict:
    """Parse NFC-e HTML and return structured data."""
    soup = BeautifulSoup(html, "html.parser")

    # Accordion1: seller + items + summary + payments
    accordion1 = soup.find(id="accordion1")
    header1 = accordion1.find(id="heading1")
    collapse1 = accordion1.find(id="collapse1")

    seller = parse_seller(header1)
    items = parse_items(collapse1)
    summary = parse_summary(collapse1)
    payments = parse_payments(collapse1)

    # Accordion2: consumer
    accordion2 = soup.find(id="accordion2")
    consumer = parse_consumer(accordion2)

    # Accordion3: access key
    accordion3 = soup.find(id="accordion3")
    access_key = parse_access_key(accordion3)

    # Accordion4: taxes (optional) — also check collapse1 for single tax line
    accordion4 = soup.find(id="accordion4")
    taxes = parse_taxes(accordion4)
    if taxes is None:
        taxes = parse_taxes_from_summary(collapse1)

    # Accordion6: invoice metadata
    accordion6 = soup.find(id="accordion6")
    invoice = parse_invoice(accordion6)
    invoice["access_key"] = access_key

    result = OrderedDict(
        [
            ("seller", seller),
            ("items", items),
            ("summary", summary),
            ("payments", payments),
            ("consumer", consumer),
            ("invoice", invoice),
        ]
    )

    if taxes:
        result["taxes"] = taxes

    return result
