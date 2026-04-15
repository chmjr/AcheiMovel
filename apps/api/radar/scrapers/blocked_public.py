from collections.abc import AsyncIterator

import httpx

from radar.scrapers.base import BaseScraper, RawListing


class BlockedPublicPageScraper(BaseScraper):
    start_url: str
    blocked_terms = ("captcha", "cloudflare", "bot manager", "access denied")

    async def discover(self) -> AsyncIterator[str]:
        yield self.start_url

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            trust_env=False,
            headers={"user-agent": "Mozilla/5.0"},
        ) as client:
            response = await client.get(url)

        lowered = response.text.lower()
        if response.status_code in {401, 403, 429} or any(term in lowered for term in self.blocked_terms):
            raise RuntimeError(f"{self.source} bloqueou a coleta pública automatizada.")
        return None


class OlxScraper(BlockedPublicPageScraper):
    source = "olx"
    category = "common"
    start_url = "https://www.olx.com.br/imoveis/venda/estado-sc/florianopolis-e-regiao/grande-florianopolis"


class ImovelwebScraper(BlockedPublicPageScraper):
    source = "imovelweb"
    category = "common"
    start_url = "https://www.imovelweb.com.br/apartamentos-venda-florianopolis-sc.html"


class VivaRealScraper(BlockedPublicPageScraper):
    source = "vivareal"
    category = "common"
    start_url = "https://www.vivareal.com.br/venda/santa-catarina/florianopolis/"


class ZapScraper(BlockedPublicPageScraper):
    source = "zap"
    category = "common"
    start_url = "https://www.zapimoveis.com.br/venda/apartamentos/sc+florianopolis/"
