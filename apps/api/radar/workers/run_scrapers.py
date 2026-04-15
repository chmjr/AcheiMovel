import argparse
import asyncio
import json

from radar.workers.scrape_jobs import (
    scrape_brognoli_async,
    scrape_caixa_async,
    scrape_chaves_na_mao_async,
    scrape_casamare_async,
    scrape_imovelweb_async,
    scrape_kzue_async,
    scrape_lanceja_async,
    scrape_leiloeiro_publico_async,
    scrape_loft_async,
    scrape_mega_leiloes_async,
    scrape_olx_async,
    scrape_quintoandar_async,
    scrape_superbid_async,
    scrape_vivareal_async,
    scrape_zap_async,
)


SCRAPERS = {
    "brognoli": scrape_brognoli_async,
    "caixa": scrape_caixa_async,
    "casamare": scrape_casamare_async,
    "chaves_na_mao": scrape_chaves_na_mao_async,
    "imovelweb": scrape_imovelweb_async,
    "kzue": scrape_kzue_async,
    "lanceja": scrape_lanceja_async,
    "loft": scrape_loft_async,
    "leiloeiro_publico": scrape_leiloeiro_publico_async,
    "mega_leiloes": scrape_mega_leiloes_async,
    "olx": scrape_olx_async,
    "quintoandar": scrape_quintoandar_async,
    "superbid": scrape_superbid_async,
    "vivareal": scrape_vivareal_async,
    "zap": scrape_zap_async,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa scrapers automáticos do Radar Imobiliário.")
    parser.add_argument("source", choices=sorted(SCRAPERS), help="Fonte que será coletada.")
    args = parser.parse_args()

    result = asyncio.run(SCRAPERS[args.source]())
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
