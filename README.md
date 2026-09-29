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
