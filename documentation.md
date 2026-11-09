# UPA projekt 2. část

**Tým:** xdomra00, xdobia15, xblaze38
**Zdrojová data:** produktové stránky e-shopu Geekbuying, <https://www.geekbuying.com/>.
**Typ produktů:** elektrické koloběžky a elektrokola.

# 1. Představení datové sady

Vstupem je výstup webového sběru z první části projektu obsahující data o elektrických koloběžkách a elektrokolech z e-shopu Geekbuying (https://www.geekbuying.com/). Záznam obsahuje URL produktu, název, cenu, značku, barvu, výkon motoru, kapacitu baterie, dojezd a maximální rychlost. Barva a značka jsou kategorické a ostatní atributy jsou numerické a jejich jednotky jsou součástí významu atributu (W, Wh, km, km/h). Cena je v měně převzaté ze vstupních dat.

Při rozdělení složeného atributu barva obsahující i více barev do samostatných řádků se počet záznamů zvýšil z 320 na 334. Výsledná tabulka obsahuje 320 různých URL, kde se některá z nich opakují i čtyřikrát, přičemž tyto opakované řádky reprezentují barevné varianty toho samého produktu.

| Atribut (typ) | Význam |
|---|---|
| `url` (text) | URL produktové stránky |
| `name` (text) | název produktu |
| `price` (numerický) | cena produktu |
| `brand` (kategorický) | výrobce/značka |
| `motor_power_w` (numerický) | výkon motoru ve wattech |
| `battery_capacity_wh` (numerický) | kapacita baterie ve watthodinách |
| `range_km` (numerický) | dojezd v kilometrech |
| `speed_kmh` (numerický) | maximální rychlost v km/h |
| `color` (kategorický) | barva výrobku |

## 1.1 Příprava zdrojové tabulky

V notebooku `task_0_cleaning.ipynb` se při načtení sjednotí názvy atributů a odstraní se prázdné řádky. Nevalidní URL, které nezačínají `http://` nebo `https://`, se vyřadí. Dále se více hodnot barev oddělených čárkou rozdělí do samostatných řádků tak, že názvy barev se převedou na malá písmena a oříznou se okrajové mezery. Neplatné či prázdné hodnoty barvy zůstávají prázdné.

Kapacita baterie je na vstupu jako text s jednotkou. Skript zkouší získat hodnotu z formátu s `Wh` a nebo ji vypočítá z napětí a kapacity ve formátu `V` a `Ah`. Po výpočtu jsou všechna data v tomto atributu ve stejných jednotkách a uděvají se tedy bez jednotky jako numerické hodnoty.

Ostatní numerické atributy se převedou na numerický typ a atribut značka se sjednotí na jednotný formát malých písmen. Už zde jsou vidět anomálie po deskriptivním popisu dat v atributech. Tyto podezřelé hodnoty se ponechají do další fáze pro analýzu (například nulové údaje nebo mimořádně vysoké hodnoty). Atribut name je pouze informativní, a tudíž je zbytečný pro další analýzu, tak ho odebereme.

# 2. Explorativní analýza

Explorativní analýza v `task_1_exploratory_analysis.ipynb` vychází z připravené tabulky o 334 řádcích. Pro numerické atributy používá popisné statistiky, histogramy a krabicové grafy, pro kategorické atributy četnosti a pro numerické dvojice bodové grafy a korelační matici. Chybějící hodnoty se zkoumají podle sloupců i podle počtu chybějících hodnot v řádku.

## 2.1 Struktura datové sady a datové typy

Analýza vychází z 334 řádků a 9 atributů, kde jsou 2 textové (`url`, `name`), 5 numerických (`price`, `motor_power_w`, `battery_capacity_wh`, `range_km`, `speed_kmh`) a 2 kategorické (`brand`, `color`). Tabulka obsahuje 320 unikátních URL a některé se opakují a odpovídají barevným variantám toho samého produktu. Proto řádky nepředstavují vždy nezávislé výrobky a je potřeba na to myslet při rozdělení množiny na trénovací a testovací data modelu.

> TODO: Popis jednotlivých sloupců uceleným textem (třeba z informací pomocí describe() metody). Konkrétně chybí třeba nejčastější hodnoty, rozsah hodnot...

## 2.2 Rozdělení numerických atributů

Rozdělení všech numerických atributů je představeno následujícími grafy. Grafy kombinují histogram a boxplot, aby ukázaly tvar rozdělení i potenciální odlehlé hodnoty.

| Atribut | Počet hodnot | Průměr | Směrodatná odchylka | Minimum | Medián | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| `price` | 331 | 31 281,17 | 26 351,81 | 3 859,81 | 26 061,78 | 169 904,92 |
| `motor_power_w` | 331 | 3 622,19 | 41 341,95 | 0 | 600 | 750 000 |
| `battery_capacity_wh` | 172 | 948,04 | 641,04 | 0 | 792 | 4 176 |
| `range_km` | 331 | 89,59 | 196,87 | 0 | 64 | 2 520 |
| `speed_kmh` | 331 | 36,00 | 24,11 | 0 | 25 | 250 |

Rozdělení cen je široké a pravostranně vychýlené, protože medián je viditelně o něco menší jak průměr. Totéž platí i u výkonu motoru, kde hodnota 750 000 několikanásobně převyšuje ostatní hodnoty a výrazně zvedá průměr, což je dokázané také obrovskou směrodatnou odchylkou. Kapacita baterie má pouze 172 hodnot, takže tento sloupec bude přibližně u poloviny dat mít chybějící hodnotu. Ostatní hodnoty jsou celkem rozumné a nejsou v nich vidět nějaké extrémně vzdálené anomálie mimo nulové hodnoty a maximální rychlosti 250 km/h a dojezdu 2 520 km.

> TODO: Tady přidat grafy pro numerické atributy a podrobně popsat zjištění.

## 2.3 Rozdělení kategorických atributů

Tato podkapitola pracuje s grafy četností kategorií. V uložených výsledcích jsou přímo doloženy grafy četností všech značek a barev a srovnání nejčastějších kategorií a jejich kombinací.

Značka má 306 hodnot a to 51 různých, kde se nejčastěji vyskytují `fafrees` (41 záznamů), `iscooter` (25 záznamů) a `joyor` (23 záznamů). Barva je známa pouze u 196 řádků a má 37 různých hodnot po rozdělení a normalizaci textu. Nejčastější barvy jsou `black` (56), `blue` (25), `grey` (19), `white` (17) a `red` (16).

> TODO: Tady přidat grafy pro kategorické atributy a podrobně popsat zjištění.

## 2.4 Odlehlé a podezřelé hodnoty

Krabicové grafy a histogramy ukazují extrémní nebo věcně nepravděpodobné hodnoty. Průměr výkonu motoru je výrazně ovlivněn maximem 750 000 W při mediánu 600 W. Nulový výkon, dojezd či rychlost jsou pravděpodobně také špatně zadané hodnoty.Dojezd až 2 520 km rovněž vyžaduje u elektrických koloběžek podorbnější ověření. Odlehlé hodnoty mohou být chybou extrakce nebo jsou v jiných jednotkách.

V rámci kategorických atributů nelze říct, zda obsahují nějaké podezřelé hodnoty. U sloupce barva dominují základní barvy a další hodnoty představují méně používané barvy, ale nic nenaznačuje, že některé hodnoty by do této datové sady neměly patřit. Atribut značka je na tom velmi podobně. Obsahuje spoustu značek, které prodávají pouze pár druhů produktů, ale nelze říct, že některá značka mezi ně nepatří.

> TODO: Napsat, jak jsme odlehlé hodnoty detekovali. Alespoň 2 metody.

## 2.5 Chybějící hodnoty

| Atribut | Chybějící hodnoty | Podíl z 334 řádků |
|---|---:|---:|
| `price` | 3 | 0,9 % |
| `brand` | 28 | 8,4 % |
| `motor_power_w` | 3 | 0,9 % |
| `battery_capacity_wh` | 162 | 48,5 % |
| `range_km` | 3 | 0,9 % |
| `speed_kmh` | 3 | 0,9 % |
| `color` | 138 | 41,3 % |
| `url`, `name` | 0 | 0 % |

Největší problém představují chybějící údaje o kapacitě baterie a barvě, kde chybí téměř polovina hodnot. Na následujícím grafu je rozložení řádků podle počtu chybějících hodnot. Některé záznamy mají dokonce 6 nebo 7 chybějících hodnot a zde nemá cenu hodnoty dopočítávat, protože zde může být mezi jednotlivými atributy korelace, která by mohla výrazně zkreslit hodnoty u těchto záznamů s téměř nulovou počáteční informací.

Téměř všechny záznamy mají chybějící maximálně 2 hodnoty. Pro tyto záznamy je vhodné dopočítat chybějící numerické atributy. U kategorických nominálních atributů, jako je barva, která má výrazný podíl chybějících hodnot v datech, bohužel nejsme schopni určit kategorii produktu a nezbývá, než nechat tyto hodnoty prázdné, nebo je vyplnit nějakou z dostupných barev nebo vyplnit náhodně vybranou barvou.

> TODO: Dodat grafy z notebooku.

## 2.6 Vztahy mezi atributy a korelační analýza

Z následujcící heatmapy vychází korelace ceny s kapacitou baterie 0,58, s rychlostí 0,36 a s dojezdem 0,35; s výkonem motoru je téměř nulová (0,01). Kapacita baterie koreluje s výkonem motoru (0,72), rychlostí (0,63) a dojezdem (0,60). Přičemž v datech se nacházejí extrémy v podobě nulových a vysokých hodnot atributů, které mohou koeficienty ovlivňovat. Korelační analýza ukazuje korelaci převážně pozue mezi kapacitou baterie a všemi ostatními atributy. Bez upravené datové sady nelze vyvodit přesnější závěr.

> TODO: Graf korelační heatmapy.

## 2.7 Shrnutí

Data kombinují elektrokola a elektrické koloběžky, které mohou mít lehce rozdílné typické hodnoty. Jednotlivé numerické atributy obsahují zjevně podezřelé extrémy a v kapacitě baterie chybí téměř polovina hodnot. Bez upraveného datasetu, který již neobsahuje extrémně odlehlé hodnoty, má opravenou většinu chybějících hodnot a zobrzuje data v očekávaném rozpětí, nelze určit hlavně přesnou korelaci mezi jednotlivými atributy.

# 3. Příprava variant pro dolování

Obě navazující varianty se načítají ze stejného `clean_data.pkl`, kde jsou z atributů vyřazeny `url` a `name`, které mají čistě jen informativní účel o výrobku a nejsou vstupními vlastnostmi zvolených metod.

## 3.1 Příprava dat pro shlukování výrobků

> TODO: Dodělat.

## 3.2 Příprava dat pro predikci ceny výrobku

> TODO: Dodělat.

## 3.3 Chybějící hodnoty a odlehlé hodnoty

> TODO: Dodělat.

# 4. Závěr

> TODO: Dodělat.
