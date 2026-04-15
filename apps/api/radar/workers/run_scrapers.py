import argparse
import json

from radar.workers.scrape_jobs import (
    scrape_brognoli,
    scrape_caixa,
    scrape_chaves_na_mao,
    scrape_imovelweb,
    scrape_lanceja,
    scrape_loft,
    scrape_leiloeiro_publico,
    scrape_mega_leiloes,
    scrape_olx,
    scrape_quintoandar,
    scrape_superbid,
    scrape_vivareal,
    scrape_zap,
)


SCRAPERS = {
    "brognoli": scrape_brognoli,
    "caixa": scrape_caixa,
    "chaves_na_mao": scrape_chaves_na_mao,
    "imovelweb": scrape_imovelweb,
    "lanceja": scrape_lanceja,
    "loft": scrape_loft,
    "leiloeiro_publico": scrape_leiloeiro_publico,
    "mega_leiloes": scrape_mega_leiloes,
    "olx": scrape_olx,
    "quintoandar": scrape_quintoandar,
    "superbid": scrape_superbid,
    "vivareal": scrape_vivareal,
    "zap": scrape_zap,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa scrapers automáticos do Radar Imobiliário.")
    parser.add_argument("source", choices=sorted(SCRAPERS), help="Fonte que será coletada.")
    args = parser.parse_args()

    result = SCRAPERS[args.source]()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
