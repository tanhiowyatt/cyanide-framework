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

# Cyanide – SSH и Telnet хонипот среднего уровня взаимодействия

**Cyanide** — это SSH и Telnet хонипот среднего уровня взаимодействия (medium-interaction), разработанный для введения в заблуждение злоумышленников и углубленного анализа их поведения. Он сочетает в себе реалистичную эмуляцию файловой системы Linux, продвинутую симуляцию команд (с поддержкой конвейеров и перенаправлений), надежные механизмы предотвращения обнаружения и гибридный ML-движок для обнаружения аномалий.

---

### Возможности

#### 1) Машинное обучение для автоматической классификации атак и извлечения IOC
- Система автоматически классифицирует сетевую активность по типам атак (brute-force, credential stuffing, разведка, попытки эксплуатации) на основе поведения сессии и характеристик полезной нагрузки (payload).
- События нормализуются с извлечением индикаторов компрометации (IOC), включая IP-адреса, порты, учетные данные, user-agent/баннеры, команды, URL-адреса, хеши артефактов и словари частоты атак.
- Генерируется сводка сессии, подробно описывающая намерения атаки, отклонения от базовых норм и рекомендуемые IOC для блокировки или интеграции в правила обнаружения.

#### 2) Повышенный реализм для предотвращения обнаружения хонипота
- Реалистичное время ответа и его вариативность (ошибки, задержки, форматы сообщений) повышают вероятность ошибочной классификации автоматическими детекторами хонипотов.
- Динамические профили среды: баннеры сервисов, версии и операционные сценарии развиваются естественно, избегая статических шаблонов.
- Человекоподобное поведение интерфейса: правдоподобные ограничения, сообщения об ошибках и незначительные несоответствия, характерные для рабочих систем.

#### 3) Расширенная интеграция с SOC и аналитикой
- Структурированные логи JSON со стандартизированной схемой событий для облегчения корреляции и поиска.
- Экспорт событий во внешние системы: стеки SIEM/логов (ELK/Splunk), уведомления через вебхуки (Slack, Discord, Telegram) в режиме реального времени.
- Поддержка пакетной обработки (batching) и контроля лимитов сообщений для предотвращения спама.
- Настраиваемые триггеры и правила для алертов по критическим паттернам (например, аномальная скорость brute-force, загрузка дропперов, подозрительные команды/нагрузки).

---

### Документация

Полные руководства по установке, настройке и интеграции доступны в нашем **[Центре документации](../index.md)**.

*   [Быстрый старт](../user-reference/QuickStart.md)
*   [Расширенная настройка](../user-reference/AdvancedUsage.md)
*   [Справочник разработчика](../developer-reference/core/index.md)

---

### Быстрый старт
 
 ```bash
1. Клонируйте репозиторий
git clone https://github.com/tanhiowyatt/cyanide-framework.git

2. Перейдите в папку проекта
cd cyanide-framework

3. Запустите среду
docker-compose up -d

4. Подключитесь через SSH, Telnet или SFTP
ssh root@localhost -p 2222
telnet localhost -p 2222
sftp root@localhost -p 2222

* С локальными изменениями
docker-compose up -d --build
```

### Быстрый старт через PyPI

```bash
1. Установите пакет
pip install cyanide-framework

2. Запустите хонипот
cyanide-framework
```

---

### Как работает фреймворк

Framework Cyanide развертывает **сервис-приманку** (decoy service) и ведет злоумышленников по **контролируемому сценарию**: он эмулирует реалистичный сервис, не предоставляя фактического доступа к хосту.

#### Динамические профили и эмуляция железа
Идентичность фреймворка определяется профилями конкретных ОС в `src/cyanide/configs/profiles/<os>/`.
- **`base.yaml`**: Главная конфигурация профиля, содержащая метаданные (версия ядра, имя хоста), honeytokens и **системные шаблоны**.
- **Системные шаблоны**: Теперь вы можете настраивать «отпечаток» оборудования прямо в YAML.
  - `cpuinfo`: Эмулируемый вывод `/proc/cpuinfo`.
  - `meminfo`: Эмулируемый вывод `/proc/meminfo`.
  - `processes`: Список фоновых процессов, которые будут отображаться в `ps` и `top`.

Пример определения железа в `base.yaml`:
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

#### Инфраструктура Libvirt (Продвинутая эмуляция)
Cyanide поддерживает опциональный **бэкенд Libvirt** для высокоточной эмуляции на базе виртуальных машин:
- **Пулы ВМ**: Автоматическое управление пулом клонов из базового образа.
- **NAT и снимки (Snapshots)**: Бесшовная настройка сети и мгновенный откат состояния для каждой сессии.
- **Готовность к Docker**: Официальный Docker-образ включает зависимости `libvirt0` для поддержки удаленных соединений Libvirt (например, `qemu+ssh://...`).

Для включения настройте раздел `pool` в вашем `cyanide.yaml`:
```yaml
pool:
  enabled: true
  mode: libvirt
  libvirt_uri: "qemu:///system"
  max_vms: 5
```

#### SQLite (Высокая производительность)
YAML служит «исходным кодом», который компилируется/кешируется в формат **SQLite** (`.compiled.db`) для использования в продакшене:
- Более быстрая загрузка и декодирование по сравнению с YAML/JSON;
- Меньший размер, проще кеширование и распространение;
- Более стабильная производительность при высоких нагрузках.

#### Поток сессии
Система обрабатывает каждое взаимодействие через структурированный **Поток сессии**:
- Входящее событие (вход/команда/нагрузка)
- Обновление состояния
- Применение правил профиля (YAML/SQLite)
- Генерация ответа (с реалистичным временем)
- Логгирование + извлечение IOC

#### Логи и IOC
Фиксируются структурированные события: IP/ID сессии, попытки входа, команды/нагрузки, время и результаты. На их основе извлекаются **IOC**, классифицируются атаки, а алерты экспортируются в системы SOC.

---

### Создатели

Этот фреймворк был создан **tanhiowyatt** и **koshanzov**. Наше первоначальное сотрудничество над продвинутыми прототипами хонипотов переросло в текущий open-source проект в области кибербезопасности, ориентированный на реалистичную симуляцию угроз, классификацию атак с использованием ML и бесшовную интеграцию с SOC.

---

### Отказ от ответственности

Это программное обеспечение предназначено только для образовательных и исследовательских целей. Запуск фреймворка сопряжен со значительными рисками. Автор не несет ответственности за любой ущерб или неправомерное использование.

---

<p align="center">
  <i>Revision: 1.0 - May 2026 - Cyanide Framework</i>
</p>
