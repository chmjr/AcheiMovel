# Fontes e coleta de dados

Este projeto prioriza coleta automatica de dados publicos de imoveis, leiloes e portais, mas sem bypass de controles de acesso.

## Permitido

- Ler paginas publicas de categoria, cidade, busca, sitemap e detalhes.
- Extrair JSON publico embutido na pagina, como `__NEXT_DATA__`, JSON-LD ou scripts de estado inicial.
- Consumir endpoints publicos observaveis no navegador quando nao exigem login, captcha, token privado ou contorno de acesso.
- Usar Playwright para renderizar paginas publicas que dependem de JavaScript.
- Aplicar rate limit, jitter, retry com backoff e circuit breaker.
- Registrar bloqueios em `scrape_runs` com erro claro.
- Guardar `raw_payload` para reprocessamento offline.

## Nao permitido

- Bypass de captcha, hCaptcha, Cloudflare, Radware Bot Manager ou protecoes equivalentes.
- Rotacao de proxies para escapar de bloqueio, banimento ou limite imposto pela fonte.
- Renovar automaticamente tokens privados, de sessao ou de autenticacao que tenham sido obtidos via navegador logado.
- Acessar dados atras de login, paywall, area restrita ou contrato que nao autorize coleta.
- Simular identidade falsa ou ocultar a automacao quando o site bloqueia explicitamente scraping.

## Como lidar com paginas dificeis

1. Tentar HTML publico com `httpx`.
2. Procurar JSON publico embutido na pagina.
3. Usar Playwright somente para renderizar conteudo publico.
4. Reduzir velocidade e usar rate limit para nao agredir a fonte.
5. Se houver captcha/bot manager/login obrigatorio, registrar falha e pausar a fonte.
6. Preferir fontes com dados publicos estaveis, parceria, exportacao ou API documentada.

## Estrategia atual

- `superbid`: usa JSON publico `__NEXT_DATA__`.
- `leiloeiro_publico`: usa HTML publico.
- `mega_leiloes`: usa paginas publicas por cidade e filtra URLs de `/imoveis/`.
- `lanceja`: usa HTML publico, filtrando regiao-alvo.
- `caixa`: atualmente bloqueada por bot manager/captcha no ambiente automatizado; o bloqueio e registrado.
