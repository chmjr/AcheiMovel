from collections.abc import AsyncIterator
from decimal import Decimal
import re
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing

CAIXA_BASE = "https://venda-imoveis.caixa.gov.br"
CAIXA_SEARCH_PAGE = f"{CAIXA_BASE}/sistema/busca-imovel.asp"


class CaixaScraper(BaseScraper):
    source = "caixa"
    category = "bank_owned"
    target_cities = ("FLORIANOPOLIS", "SAO JOSE", "PALHOCA", "BIGUACU")

    async def discover(self) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(CAIXA_SEARCH_PAGE)
            html = response.text
            if _is_blocked(html):
                raise RuntimeError("Caixa bloqueou a coleta automatizada com bot manager/captcha.")

            for url in _extract_detail_urls(html):
                yield url

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url)
            html = response.text

        if _is_blocked(html):
            raise RuntimeError("Caixa bloqueou o detalhe do imóvel com bot manager/captcha.")

        fields = _extract_fields(html)
        source_id = fields.get("matricula") or fields.get("matrícula") or url.rsplit("=", 1)[-1]
        price = parse_brl(fields.get("valor de venda") or fields.get("valor venda"))
        appraisal = parse_brl(fields.get("valor de avaliação") or fields.get("valor avaliacao"))

        return RawListing(
            source=self.source,
            source_id=source_id,
            source_url=url,
            title=fields.get("tipo de imóvel") or fields.get("tipo imovel") or "Imóvel Caixa",
            description=fields.get("descrição") or fields.get("descricao"),
            price=price,
            condo_fee=None,
            iptu_yearly=None,
            city=fields.get("cidade") or "Não informado",
            neighborhood=fields.get("bairro"),
            address=fields.get("endereço") or fields.get("endereco"),
            property_type=normalize_property_type(fields.get("tipo de imóvel") or fields.get("tipo imovel")),
            area_privative=parse_area(fields.get("área privativa") or fields.get("area privativa")),
            bedrooms=parse_int(fields.get("quartos")),
            bathrooms=parse_int(fields.get("banheiros")),
            parking_spots=parse_int(fields.get("vagas")),
            photos=_extract_photos(html),
            raw_payload={"url": url, "fields": fields, "html": html},
            bank_data={
                "bank": "caixa",
                "sale_modality": fields.get("modalidade de venda") or fields.get("modalidade venda"),
                "discount_pct": compute_discount(appraisal, price),
                "financeable": contains_truthy(fields, "financiamento"),
                "fgts_allowed": contains_truthy(fields, "fgts"),
                "minimum_entry_pct": None,
            },
        )


def _is_blocked(html: str) -> bool:
    lowered = html.lower()
    return "bot manager block" in lowered or "hcaptcha" in lowered or "captcha" in lowered


def _extract_detail_urls(html: str) -> list[str]:
    urls = set()
    for match in re.finditer(r"detalhe[-_]imovel\.asp\?[^'\"<>\s]+", html, re.IGNORECASE):
        urls.add(urljoin(CAIXA_BASE, f"/sistema/{match.group(0)}"))
    for match in re.finditer(r"detalhe_imovel\(['\"]?(\d+)['\"]?\)", html, re.IGNORECASE):
        urls.add(f"{CAIXA_BASE}/sistema/detalhe-imovel.asp?hdnImovel={match.group(1)}")
    return sorted(urls)


def _extract_fields(html: str) -> dict[str, str]:
    tree = HTMLParser(html)
    text = tree.body.text(separator="\n") if tree.body else tree.text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = _normalize_key(key)
        value = value.strip()
        if key and value and key not in fields:
            fields[key] = value
    return fields


def _extract_photos(html: str) -> list[str]:
    tree = HTMLParser(html)
    photos = []
    for img in tree.css("img"):
        src = img.attributes.get("src")
        if src and any(token in src.lower() for token in ["foto", "imagem", "imovel"]):
            photos.append(urljoin(CAIXA_BASE, src))
    return photos


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_brl(value: str | None) -> Decimal | None:
    if not value:
        return None
    clean = re.sub(r"[^\d,.-]", "", value)
    if not clean:
        return None
    clean = clean.replace(".", "").replace(",", ".")
    try:
        return Decimal(clean)
    except Exception:
        return None


def parse_area(value: str | None) -> Decimal | None:
    return parse_brl(value)


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def normalize_property_type(value: str | None) -> str:
    lowered = (value or "").lower()
    if "casa" in lowered:
        return "casa"
    if "terreno" in lowered:
        return "terreno"
    if "apart" in lowered:
        return "apartamento"
    return "imovel"


def compute_discount(appraisal: Decimal | None, price: Decimal | None) -> Decimal | None:
    if not appraisal or not price or appraisal <= 0:
        return None
    return ((appraisal - price) / appraisal * Decimal("100")).quantize(Decimal("0.01"))


def contains_truthy(fields: dict[str, str], needle: str) -> bool | None:
    joined = " ".join(fields.values()).lower()
    if needle in joined:
        return True
    return None
