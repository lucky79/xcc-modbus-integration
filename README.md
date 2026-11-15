# AC Heating xCC pro Home Assistant

Vlastní integrace pro tepelná čerpadla AC Heating Convert AW s regulátorem xCC. Komunikuje v místní síti přes Modbus TCP. Mapa registrů vychází z dokumentace protokolu 2.5 pro xCC 5.9/8.5 a z příkladu výrobce pro Loxone.

## Instalace

Vyžaduje Home Assistant 2026.2 nebo novější. Integrace používá knihovnu PyModbus dodanou vestavěnou integrací Modbus.

### HACS

1. V HACS otevřete nabídku **Vlastní repozitáře**.
2. Přidejte `https://github.com/lucky79/xcc-modbus-integration` v kategorii **Integrace**.
3. Vyhledejte **AC Heating xCC**, stáhněte ji a restartujte Home Assistant.

### Ruční instalace

Zkopírujte složku `custom_components/xcc_modbus` z repozitáře do konfigurační složky Home Assistantu. Výsledná cesta k manifestu má být `/config/custom_components/xcc_modbus/manifest.json`. Poté restartujte Home Assistant.

## Připojení

1. V Home Assistantu otevřete **Nastavení → Zařízení a služby → Přidat integraci** a vyhledejte **AC Heating xCC**.
2. Zadejte IP adresu nebo název regulátoru. Výchozí port TCP je **502**, adresa zařízení Modbus je pevně **1** a výchozí interval čtení je **15 sekund**.
3. Vyplňte počet aktivních topných okruhů (0–12), zásobníků TUV (0–2), samostatných zón (0–16) a externích teplotních vstupů (0–16). Výchozí nastavení je jeden topný okruh, jeden zásobník a žádné zóny ani externí vstupy. Číslování skupin začíná od 1.
4. Podle výbavy vyberte počet venkovních jednotek (1–10), bazénů (0–2) a měřičů M-Bus (0–4). V poli **Volitelné skupiny registrů** lze přidat sběrnicový elektroměr, fotovoltaiku, omezení výkonu a časové programy cirkulace TUV 1. Výchozí nastavení je jedna venkovní jednotka, žádný bazén ani měřič M-Bus a prázdný seznam volitelných skupin.

xCC umožňuje jedno aktivní spojení Modbus TCP. Před přidáním integrace ukončete připojení Loxone, jiného klienta Modbus nebo paralelní konfigurace téhož regulátoru. Pro změnu adresy nebo počtu okruhů použijte volbu **Překonfigurovat** v nabídce integrace.

## Dostupné entity

Od Home Assistantu 2026.9 se pod zařízením **AC Heating xCC** zobrazují podřízená zařízení podle vybrané výbavy. Topení zahrnuje i samostatné zóny a externí teplotní vstupy. Systémové údaje jsou na hlavním zařízení. Stávající entity si po aktualizaci zachovají ID. Ve starších verzích Home Assistantu jsou všechny entity na hlavním zařízení.

### Aktuální elektrický příkon

V nabídce **Překonfigurovat → Volitelné skupiny registrů** vyberte **Sběrnicový elektroměr (příkon a spotřeba)**. V podřízeném zařízení **Elektroměr** se objeví **Celkový aktuální příkon** v kW, jednotlivé fáze ve W a spotřeba v kWh. Celkový příkon je součet fází L1, L2 a L3 z holding registrů 357–359. Měřená hodnota vyžaduje sběrnicový elektroměr zapojený a nastavený v xCC a odpovídá rozsahu měření tohoto elektroměru. Výkon kompresoru v procentech má vlastní entitu.

### Přehled registrů

| Oblast | Čtení | Ovládání |
| --- | --- | --- |
| Systém | Venkovní teplota včetně nefiltrované hodnoty, výstupní, požadovaná a vratná teplota, výkon systému a první venkovní jednotky v %, poruchy, HDO, stav, blokování a motohodiny bivalence | Hlavní vypínač a ignorování HDO (v registru entit zakázané ve výchozím stavu) |
| Topné okruhy | Teplota místnosti, teplota topné vody a aktivita | Povolení okruhu, požadovaná teplota místnosti, režim konstantní teploty vody a její nastavení, režim prostoru |
| Akumulace | Teplota akumulační nádrže (holding registr 95, měřítko 100) a stav „Akumulace aktivní“ (coil 32) | — |
| TUV | Teplota zásobníku a zpátečky, aktivita ohřevu, externí ohřev a jeho motohodiny, aktivita a časy sanitace, stav cirkulace TUV 1 | Povolení ohřevu a jeho cílové teploty, parametry sanitace, vynucený externí ohřev a řízení cirkulace TUV 1 |
| Samostatné zóny | Teplota vzduchu, stav vytápění a požadované otevření ventilu | Povolení vytápění a požadovaná teplota |
| Externí vstupy | Poslední načtená teplota externího vstupu | Předání naměřené teploty z čidla v Home Assistantu akcí `number.set_value` |
| Venkovní jednotky | Teploty chladicího okruhu, otáčky ventilátorů, motohodiny kompresoru, výkon v % a průtok výměníkem | — |
| Kotel na tuhá paliva | Teplota a aktivita | — |
| Bazén | Skutečná teplota bazénu 1 | Povolení bazénů 1 a 2, cílová teplota, plán vytápění a filtrace bazénu 1 |
| Elektroměr | Příkon podle fází, celkový příkon, spotřeba podle fází a celková spotřeba | — |
| Fotovoltaika | Přetok fází včetně interních hodnot Cascade a SSR | — |
| M-Bus | Osm datových polí a stav každého ze čtyř měřičů | — |
| Omezení výkonu | Aktuální nastavení | Limity, povolení, práh, hystereze a časový program |
| Programy cirkulace TUV 1 | Aktuální nastavení | Dva týdenní programy a doby cyklovače |

Při použití konstantní teploty topné vody zapněte u daného okruhu **režim konstantní teploty**. Volba teplotního čidla pro okruh a nastavení vícezónové regulace se provádí v xCC. Pro referenční místnost nebo jednotlivé zóny použijte automatizaci odesílající hodnotu čidla do externího vstupu při změně měření. Při nedostupnosti čidla zápis přeskočte. Při použití ručního ovládání cirkulace zapněte přepínač ručního režimu a následně nastavte požadovaný stav oběhového čerpadla.

Hodnoty se po zápisu načítají z regulátoru. Je-li jednotlivá adresa odmítnuta jako nepodporovaná, Home Assistant zobrazuje její entitu jako nedostupnou. Při výpadku spojení se čtení automaticky obnoví po návratu regulátoru.

### Interpretace registrů

- Dokumentace uvádí měřítko 100 pro teploty. Integrace používá znaménkový 16bitový formát, aby zobrazila i záporné teploty.
- Pro ventily 16 samostatných zón se používají holding registry 72–87 podle tabulky protokolu. Hodnotu integrace dělí 100 a zobrazuje bez jednotky, protože tabulka u otevření ventilu uvádí °C.
- Uživatelské rozsahy zápisu jsou nastavené v integraci. Pokojové teploty mají rozsah 5–35 °C, konstantní teplota topné vody a cíle ohřevu TUV 10–65 °C, sanitační teplota 50–75 °C, interval sanitace 1–365 dní a externí vstupy −40 až 80 °C. Povolené hodnoty na konkrétní instalaci závisejí na konfiguraci xCC.
- Časové plány a doby cyklovače jsou číselné hodnoty `HHMM`. Zapište například `630` pro 06:30. Minuty mají rozsah 00–59, konec dne lze zadat jako `2400`.
- Dokumentace uvádí u prahu a hystereze teplotního omezení nejasné jednotky. Obě entity proto zobrazují hodnotu registru bez jednotky. Před ovládáním je lze povolit v registru entit Home Assistantu.
- Spotřeba elektroměru a datová pole M-Bus jsou dvojice registrů čtené jako 32bitová celá čísla bez znaménka. Dokumentace pořadí slov neurčuje. Výchozí je vyšší slovo první, pořadí lze změnit v nabídce **Překonfigurovat**. Datová pole a stav M-Bus se zobrazují bez přiřazené fyzikální jednotky, protože jejich význam závisí na měřiči.
- Při zapnutí všech skupin integrace pokrývá 449 dokumentovaných adres holding registrů a 125 coil adres z mapy 2.5. Dostupnost hodnot závisí na firmwaru a vybavení xCC.
