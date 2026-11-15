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

xCC umožňuje jedno aktivní spojení Modbus TCP. Před přidáním integrace ukončete připojení Loxone, jiného klienta Modbus nebo paralelní konfigurace téhož regulátoru. Pro změnu adresy nebo počtu okruhů použijte volbu **Překonfigurovat** v nabídce integrace.

## Dostupné entity

Od Home Assistantu 2026.9 se pod zařízením **AC Heating xCC** zobrazují samostatná podřízená zařízení **Topení**, **Akumulace** a **Teplá užitková voda**. Topení zahrnuje i samostatné zóny a externí teplotní vstupy. Systémové údaje jsou na hlavním zařízení. Po aktualizaci se stávající entity přesunou do příslušných zařízení se stejnými ID. Ve starších verzích Home Assistantu jsou všechny entity na hlavním zařízení.

| Oblast | Čtení | Ovládání |
| --- | --- | --- |
| Systém | Venkovní, výstupní, požadovaná a vratná teplota, výkon systému a první venkovní jednotky v %, poruchy, HDO a stav bivalence | Hlavní vypínač, ve výchozím stavu zakázaný v registru entit Home Assistantu |
| Topné okruhy | Teplota místnosti, teplota topné vody a aktivita | Povolení okruhu, požadovaná teplota místnosti, přepnutí mezi ekvitermní regulací a konstantní teplotou vody, nastavení konstantní teploty |
| Akumulace | Teplota akumulační nádrže (holding registr 95, měřítko 100) a stav „Akumulace aktivní“ (coil 32) | — |
| TUV | Teplota zásobníku, aktivita ohřevu, externí ohřev, aktivita a čas od poslední sanitace. U TUV 1 také stav cirkulace | Povolení ohřevu, minimální a maximální teplota, povolení, teplota a interval sanitace. U TUV 1 také povolení a ruční ovládání cirkulace |
| Samostatné zóny | Teplota vzduchu, stav vytápění a požadované otevření ventilu | Povolení vytápění a požadovaná teplota |
| Externí vstupy | Poslední načtená teplota externího vstupu | Předání naměřené teploty z čidla v Home Assistantu akcí `number.set_value` |

Při použití konstantní teploty topné vody zapněte u daného okruhu **režim konstantní teploty**. Volba teplotního čidla pro okruh a nastavení vícezónové regulace se provádí v xCC. Pro referenční místnost nebo jednotlivé zóny použijte automatizaci odesílající hodnotu čidla do externího vstupu při změně měření. Při nedostupnosti čidla zápis přeskočte. Při použití ručního ovládání cirkulace zapněte přepínač ručního režimu a následně nastavte požadovaný stav oběhového čerpadla.

Hodnoty se po zápisu načítají z regulátoru. Je-li jednotlivá adresa odmítnuta jako nepodporovaná, Home Assistant zobrazuje její entitu jako nedostupnou. Při výpadku spojení se čtení automaticky obnoví po návratu regulátoru.

### Interpretace registrů

- Dokumentace uvádí měřítko 100 pro teploty. Integrace používá znaménkový 16bitový formát, aby zobrazila i záporné teploty.
- Pro ventily 16 samostatných zón se používají holding registry 72–87 podle tabulky protokolu. Hodnotu integrace dělí 100 a zobrazuje bez jednotky, protože tabulka u otevření ventilu uvádí °C.
- Uživatelské rozsahy zápisu jsou nastavené v integraci. Pokojové teploty mají rozsah 5–35 °C, konstantní teplota topné vody a cíle ohřevu TUV 10–65 °C, sanitační teplota 50–75 °C, interval sanitace 1–365 dní a externí vstupy −40 až 80 °C. Povolené hodnoty na konkrétní instalaci závisejí na konfiguraci xCC.
- Tato verze pokrývá rozsah uvedený v tabulce entit. Bazén, FVE, měřiče, časové plány a omezení výkonu zůstávají k dispozici v regulátoru xCC.
