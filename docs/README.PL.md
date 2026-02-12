# Cyanide Honeypot 2.1 🛡️

**Cyanide** to honeypot SSH i Telnet o wysokiej interakcji, zaprojektowany do zwodzenia i analizowania zachowań atakujących. Łączy w sobie realistyczną emulację systemu plików Linux, zaawansowaną symulację komend oraz głębokie mechanizmy zapobiegające wykryciu.

---

### 🌐 Tłumaczenia / Translations / Переводы
*   🇺🇸 [English (Angielski)](../README.md)
*   🇷🇺 [Russian (Rosyjski)](README.RU.md)

---

## 🌟 Główne Funkcje

### 🧠 Realistyczna Emulacja
*   **Wieloprotokołowość**: Jednoczesna obsługa SSH (przez `asyncssh`) i Telnet na różnych portach.
*   **Dynamiczny System Plików**: W pełni funkcjonalny system plików Linux. Zmiany (tworzenie plików, usuwanie) persistują przez całą sesję.
*   **Zaawansowany Shell**: Obsługa potoków (`|`), przekierowań (`>`, `>>`) oraz łączenia poleceń (`&&`, `||`, `;`).
*   **Anti-Fingerprinting**: 
    *   **Network Jitter**: Losowe opóźnienia odpowiedzi (50-300ms) w celu symulacji realnej sieci.
    *   **Profile Systemowe**: Maskowanie jako **Ubuntu**, **Debian** lub **CentOS** (banery, `uname`, `/proc/version`).

### 📊 Informatyka Śledcza i Logowanie
*   **Nagrywanie TTY**: Rejestracja sesji w formacie kompatybilnym z `scriptreplay`.
*   **Strukturalny JSON**: Szczegółowe logi zdarzeń w formacie JSON dla integracji z ELK/Splunk.
*   **Biometria Klawiatury**: Analiza rytmu pisania w celu odróżnienia botów od ludzi.
*   **Kwarantanna**: Automatyczna izolacja plików pobranych przez `wget`, `curl`, `scp` lub `sftp`.
*   **VirusTotal**: Automatyczne skanowanie podejrzanych plików w kwarantannie.

---

## 🏗️ Architektura i Struktura

Projekt zbudowany jest na zasadzie modułowej z wykorzystaniem nowoczesnych wzorców Pythona:
*   **Wzorzec Fasada**: Główne funkcje są dostępne bezpośrednio z korzeni pakietów (np. `from core import HoneypotServer`).
*   **Rejestr Komend**: Dynamiczne ładowanie emulowanych komend poprzez centralny rejestr w `src/commands`.

### Struktura Katalogów
| Ścieżka | Opis |
|---------|-------------|
| `scripts/` | Narzędzia do zarządzania i kontroli |
| `config/` | Pliki konfiguracyjne (`cyanide.cfg`) i szablony ФС |
| `src/cyanide/core/` | Rdzeń serwera, emulator shella i logika systemu plików |
| `src/cyanide/commands/` | Implementacje emulowanych komend Linux |
| `var/log/cyanide/` | Logi JSON i nagrania TTY |
| `var/lib/cyanide/` | Przechowywanie danych i kwarantanna |

---

## 🚀 Wdrożenie i Obsługa
 
 **Uwaga: Ten projekt jest przeznaczony wyłącznie do uruchamiania w Dockerze.**
 
 ### 🐳 Docker Compose (Wymagane)
 Najszybszy i najbezpieczniejszy sposób uruchomienia.
 
 ```bash
 # Zbuduj i uruchom w tle
 docker compose -f docker/docker-compose.yml up --build -d
 
 # Podgląd logów serwera w czasie rzeczywistym
 docker compose -f docker/docker-compose.yml logs -f cyanide
 ```

---

## 🛠️ Materiały Narzędziowe (`scripts/`)

| Narzędzie | Opis |
|-----------|-------------|
| `./scripts/cyanide` | Główny skrypt zarządzający (start, stop, status, restart). |
| `./scripts/cyanide-replay` | Odtwarzacz logów TTY. |
| `./scripts/cyanide-clean` | Narzędzie do czyszczenia starych logów i plików w kwarantannie. |

---

## ⌨️ Emulowane Komendy

Cyanide obsługuje ponad 25 standardowych komend Linux, w tym:
*   **Nawigacja**: `cd`, `ls`, `pwd`.
*   **Operacje na plikach**: `cat`, `touch`, `mkdir`, `rm`, `cp`, `mv`, `id`.
*   **Informacyjne**: `uname`, `ps`, `whoami`, `who`, `w`, `help`.
*   **Zaawansowane**: `sudo`, `export`, `echo`.
*   **Sieciowe**: `curl`, `ping`, `wget` (z plikami zapisanymi w kwarantannie).
*   **Edytory**: `vi`, `vim`, `nano` (symulacja).

---

## 🕵️ Analiza Sesji (Scriptreplay)

Wszystkie sesje są nagrywane w `var/log/cyanide/tty/`. Każda sesja ma własny folder z plikiem danych (`.log`) i plikiem czasu (`.timing`).

**Jak odtworzyć sesję:**
1.  Znajdź odpowiedni folder sesji w `var/log/cyanide/tty/`.
2.  Wykonaj polecenie:
```bash
./scripts/cyanide-replay var/log/cyanide/tty/<dir>/
```

## 💾 Konfiguracja systemu plików (YAML)

System plików honeypot jest zdefiniowany w szablonach YAML w `config/fs-config/`.

### 🌍 Profile OS
Cyanide obsługuje kilka profili OS dla realizmu:
- **Ubuntu 22.04**
- **Debian 11**
- **CentOS 7**

### 📝 Ręczna edycja
Główny system plików zdefiniowany jest w `config/fs-config/fs.yaml`. Po prostu edytuj plik YAML aby dodać honey-pliki:

```yaml
- name: passwords.txt
  type: file
  content: "admin:SuperSecret123!"
```

### 🎯 Personalizacja profili
Użyj `generate_profiles.py`, aby zaktualizować YAML specyficzne dla dystrybucji:
```bash
python3 generate_profiles.py
```

**Skrypty nie są potrzebne do jednorazowych testów** — po prostu edytuj `config/fs-config/fs.yaml` i zrestartuj honeypot.

---

## 🧹 Konserwacja

Po długim czasie pracy zaleca się wyczyszczenie logów:
```bash
# Usuń logi starsze niż 7 dni
./scripts/cyanide-clean --days 7 --force
```

---

## ⚠️ Ostrzeżenie
To oprogramowanie służy **wyłącznie do celów edukacyjnych i badawczych**. Uruchamianie honeypota wiąże się z ryzykiem. Autor nie ponosi odpowiedzialności za jakiekolwiek szkody.
