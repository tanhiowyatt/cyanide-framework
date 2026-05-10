<p align="center">

  [![Stars](https://img.shields.io/github/stars/tanhiowyatt/cyanide-framework?style=flat&logo=GitHub&color=yellow)](https://github.com/tanhiowyatt/cyanide-framework/stargazers)
  [![CI](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/ci.yml)
  [![Security Scan](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/security_scan.yml/badge.svg)](https://github.com/tanhiowyatt/cyanide-framework/actions/workflows/security_scan.yml)
  [![Quality gate](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_framework&metric=alert_status)](https://sonarcloud.io/dashboard?id=tanhiowyatt_cyanide_framework)
  [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_framework&metric=coverage)](https://sonarcloud.io/component_measures/metric/coverage/list?id=tanhiowyatt_cyanide_framework)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/tanhiowyatt/cyanide-framework)
</p>

<p align="center">
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/README.md">ENG</a> &nbsp; | &nbsp;
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/docs/translations/readme-ru.md">RU</a> &nbsp; | &nbsp;
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-framework/blob/main/docs/translations/readme-pl.md">PL</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/tanhiowyatt/cyanide-framework/main/src/cyanide/assets/branding/name.png" alt="Cyanide" width="500" height="auto">
</p>

# Cyanide - Honeypot SSH i Telnet o średnim poziomie interakcji

**Cyanide** to honeypot SSH i Telnet o średnim poziomie interakcji (medium-interaction), zaprojektowany w celu zmylenia atakujących i dogłębnej analizy ich zachowań. Łączy w sobie realistyczną emulację systemu plików Linux, zaawansowaną symulację komend (z obsługą potoków i przekierowań), solidne mechanizmy zapobiegające wykryciu oraz hybrydowy silnik ML do wykrywania anomalii.

---

### Funkcje

#### 1) Machine Learning do automatycznej klasyfikacji ataków i ekstrakcji IOC
- System automatycznie kategoryzuje aktywność sieciową na typy ataków (brute-force, credential stuffing, rekonesans, próby eksploitacji) na podstawie zachowania sesji i charakterystyki ładunku (payload).
- Zdarzenia są normalizowane wraz z ekstrakcją wskaźników kompromitacji (IOC), w tym adresów IP, portów, danych uwierzytelniających, user-agentów/banerów, komend, adresów URL, haszy artefaktów i słowników częstotliwości ataków.
- Generowane jest podsumowanie sesji, szczegółowo opisujące zamiary ataku, odchylenia od norm bazowych oraz zalecane IOC do blokowania lub integracji z reguami wykrywania.

#### 2) Zwiększony realizm w celu uniknięcia wykrycia honeypota
- Realistyczne czasy odpowiedzi i ich zmienność (błędy, opóźnienia, formaty komunikatów) zwiększają wskaźnik błędnej klasyfikacji przez automatyczne detektory honeypotów.
- Dynamiczne profile środowiska: banery usług, wersje i scenariusze operacyjne rozwijają się naturalnie, unikając statycznych szablonów.
- Zachowanie interfejsu imitujące człowieka: wiarygodne ograniczenia, komunikaty o błędach i drobne niespójności charakterystyczne dla systemów produkcyjnych.

#### 3) Zaawansowane integracje SOC i analityczne
- Strukturalne logi JSON ze ustandaryzowanym schematem zdarzeń ułatwiającym korelację i wyszukiwanie.
- Eksport zdarzeń do systemów zewnętrznych: stosy SIEM/logów (ELK/Splunk), powiadomienia webhook (Slack, Discord, Telegram) w czasie rzeczywistym.
- Obsługa przetwarzania wsadowego (batching) i kontroli limitów komunikatów w celu zapobiegania spamowi i blokadom platform.
- Konfigurowalne triggery i reguły dla alertów o krytycznych wzorcach (np. anomalna prędkość brute-force, przesyłanie dropperów, podejrzane komendy/ładunki).

---

### Dokumentacja

Aby uzyskać pełne instrukcje dotyczące instalacji, konfiguracji i integracji, odwiedź nasze **[Centrum Dokumentacji](../index.md)**.

*   [Szybki start](../user-reference/QuickStart.md)
*   [Zaawansowana konfiguracja](../user-reference/AdvancedUsage.md)
*   [Referencja deweloperska](../developer-reference/core/index.md)

---

### Szybki start
 
 ```bash
1. Sklonuj repozytorium
git clone https://github.com/tanhiowyatt/cyanide-framework.git

2. Przejdź do folderu projektu
cd cyanide-framework

3. Uruchom środowisko
docker-compose up -d

4. Połącz się przez SSH, Telnet lub SFTP
ssh root@localhost -p 2222
telnet localhost -p 2222
sftp root@localhost -p 2222

* Z lokalnymi zmianami
docker-compose up -d --build
```

### Szybki start przez PyPI

```bash
1. Zainstaluj pakiet
pip install cyanide-framework

2. Uruchom honeypot
cyanide-framework
```

---

### Jak działa framework

Framework Cyanide wdraża **usługę-pułapkę** (decoy service) i prowadzi atakujących przez **kontrolowany scenariusz**: emuluje realistyczną usługę bez przyznawania rzeczywistego dostępu do hosta.

#### Dynamiczne profile i emulacja sprzętu
Tożsamość frameworka jest definiowana przez profile specyficzne dla systemu operacyjnego w `src/cyanide/configs/profiles/<os>/`.
- **`base.yaml`**: Główna konfiguracja profilu, zawierająca metadane (wersja jądra, nazwa hosta), honeytokens i **szablony systemowe**.
- **Szablony systemowe**: Możesz teraz dostosować „odcisk palca” sprzętu bezpośrednio w YAML.
  - `cpuinfo`: Emulowany wynik `/proc/cpuinfo`.
  - `meminfo`: Emulowany wynik `/proc/meminfo`.
  - `processes`: Lista procesów w tle, które pojawią się w `ps` i `top`.

Przykład definicji sprzętu w `base.yaml`:
```yaml
system_templates:
  cpuinfo: |
    vendor_id	: GenuineIntel
    model name	: Intel(R) Xeon(R) Gold 6140 CPU @ 2.30GHz
    ...
  processes:
    - pid: 1
      user: root
      cmd: "/sbin/init"
```

#### Infrastruktura Libvirt (Zaawansowana emulacja)
Cyanide obsługuje opcjonalny **backend Libvirt** dla wysokiej jakości emulacji opartej na maszynach wirtualnych:
- **Pule VM**: Automatyczne zarządzanie pulą klonów z obrazu bazowego.
- **NAT i migawki (Snapshots)**: Bezproblemowe sieciowanie i natychmiastowe przywracanie stanu dla każdej sesji.
- **Gotowy na Docker**: Oficjalny obraz Docker zawiera zależności `libvirt0`, aby wspierać zdalne połączenia Libvirt (np. `qemu+ssh://...`).

Aby włączyć, skonfiguruj sekcję `pool` w pliku `cyanide.yaml`:
```yaml
pool:
  enabled: true
  mode: libvirt
  libvirt_uri: "qemu:///system"
  max_vms: 5
```

#### SQLite (Szybki czas wykonywania)
YAML służy jako "kod źródłowy", kompilowany/buforowany do formatu **SQLite** (`.compiled.db`) na potrzeby produkcyjne:
- Szybsze ładowanie/dekodowanie niż YAML/JSON;
- Mniejszy rozmiar, łatwiejsze buforowanie/dystrybucja;
- Stabilniejsza wydajność przy wysokim obciążeniu.

#### Przepływ sesji
System przetwarza każdą interakcję poprzez ustrukturyzowany **Przepływ sesji**:
- Przychodzące zdarzenie (logowanie/komenda/ładunek)
- Aktualizacja stanu
- Zastosowanie reguł profilu (YAML/SQLite)
- Generowanie odpowiedzi (z realistycznym czasem)
- Logowanie + ekstrakcja IOC

#### Logi i IOC
Przechwytywane są strukturalne zdarzenia: IP/ID sesji, próby logowania, komendy/ładunki, czasy i wyniki. Na tej podstawie ekstrahowane są **IOC**, klasyfikowane ataki, a alerty eksportowane do systemów SOC.

---

### Twórcy

Ten framework został stworzony przez **tanhiowyatt** i **koshanzov**. Nasza początkowa współpraca nad zaawansowanymi prototypami honeypotów ewoluowała w obecny projekt open-source z dziedziny cyberbezpieczeństwa, skoncentrowany na realistycznej symulacji zagrożeń, klasyfikacji ataków z wykorzystaniem ML oraz bezproblemowej integracji z SOC.

---

### Ostrzeżenie

To oprogramowanie służy wyłącznie do celów edukacyjnych i badawczych. Uruchamianie frameworka wiąże się ze znacznym ryzykiem. Autor nie ponosi odpowiedzialności za jakiekolwiek szkody lub niewłaściwe użycie.

---

<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>
