# UPA-parsing

### Team: xdomra00

### Eshop: 
https://www.geekbuying.com/

### Parse URL (Scooters + Bicycles): 
https://www.geekbuying.com/category/E-Bikes-Scooters-Wheels-1794

### Columns: 
| url | name | price | brand | colors | motor power | battery power capacity | range | speed |
|---|---|---|---|---|---|---|---|---|


### Poznámky

- Projekt byl vyplněn třičlenným týmem: `xdomra00`, `xbobia15`, `xblaze38` - každý člen měl za úlohu implementovat vlastní skritpy které pak byly sjednoceny ve skriptech `get_urls.py` a `parse_urls.py` přesně splnující zadání 

- další zajímavosti je `llm_parse.py` se servicem `requesty.ai`  - výužíva llm na parsing slabě strukturovaných popisů položek. ($0.0001 per request)


### robots.txt
byl použit vlastní, nezakázaný User-Agent na nezakázaných endpointech

### HOW TO RUN
1. make files executable `chmod +x ./build.sh && chmod +x ./run.sh`
2. build the project `./build.sh`
3. run the demo `./run.sh`

### LLM parsing
Tato část je pouze informativní a pro spuštění demonstračního řešení nevyžaduje nic nad rámec původního zadání.
- Různí distributoři používají vlastní formáty a styly popisu produktových charakteristik.
Modul `llm_parse.py` umožňuje zpracovat libovolný popis produktu do schématu s požadovanými datovými sloupci.
- Pro demonstraci je použit levný hostovaný model s omezeným počtem požadavků za sekundu (RPS), což je dostačující pro 10–20 řádků. Pro větší datasety (např. `data.tsv`) je použit lokální model, aby se předešlo nákladům na API.
