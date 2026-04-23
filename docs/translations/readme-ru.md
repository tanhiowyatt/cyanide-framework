[![Stars](https://img.shields.io/github/stars/tanhiowyatt/cyanide-honeypot?style=flat&logo=GitHub&color=yellow)](https://github.com/tanhiowyatt/cyanide-honeypot/stargazers)
[![CI](https://github.com/tanhiowyatt/cyanide-honeypot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/tanhiowyatt/cyanide-honeypot/actions/workflows/ci.yml)
[![Security Scan](https://github.com/tanhiowyatt/cyanide-honeypot/actions/workflows/security_scan.yml/badge.svg)](https://github.com/tanhiowyatt/cyanide-honeypot/actions/workflows/security_scan.yml)
[![Quality gate](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_honeypot&metric=alert_status)](https://sonarcloud.io/dashboard?id=tanhiowyatt_cyanide_honeypot)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=tanhiowyatt_cyanide_honeypot&metric=coverage)](https://sonarcloud.io/component_measures/metric/coverage/list?id=tanhiowyatt_cyanide_honeypot)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-honeypot/blob/main/README.md">ENG</a> &nbsp; | &nbsp;
  <a target="_blank" href="https://github.com/tanhiowyatt/cyanide-honeypot/blob/main/docs/translations/readme-pl.md">PL</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/tanhiowyatt/cyanide-honeypot/main/src/cyanide/assets/branding/name.png" alt="Cyanide" width="500" height="auto">
</p>

# Cyanide – Honeypot SSH и Telnet среднего уровня взаимодействия

**Cyanide** — это honeypot SSH и Telnet среднего уровня взаимодействия (medium-interaction), разработанный для введения в заблуждение злоумышленников и углубленного анализа их поведения. Он сочетает в себе реалистичную эмуляцию файловой системы Linux, продвинутую симуляцию команд (с поддержкой конвейеров и перенаправлений), надежные механизмы предотвращения обнаружения и гибридный ML-движок для обнаружения аномалий.

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
- Экспорт событий во внешние системы: стеки SIEM/логов (ELK/Splunk), уведомления через вебхуки (Slack/Discord/Telegram) в режиме реального времени.
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
git clone https://github.com/tanhiowyatt/cyanide-honeypot.git

2. Перейдите в папку проекта
cd cyanide-honeypot

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
pip install cyanide-honeypot

2. Запустите honeypot
cyanide-honeypot
```

---

### Как работает хонипот

Honeypot Cyanide развертывает **сервис-приманку** (decoy service) и ведет злоумышленников по **контролируемому сценарию**: он эмулирует реалистичный сервис, не предоставляя фактического доступа к хосту.

#### Профили YAML (Основа поведения)
Поведение сервиса определяется через **профили YAML**:
- Эмулируемые функции (баннеры/версии, ошибки, ограничения);
- Логика ответов (правила/шаблоны, ветвление);
- Состояние сессии (аутентификация, контекст, счетчики);
- Факторы реализма (задержки/джиттер, рандомизация).

#### SQLite (Быстрое выполнение)
YAML служит «исходным кодом», который компилируется/кешируется в формат **SQLite** (`.compiled.db`) для использования в продакшене:
- Более быстрая загрузка и декодирование по сравнению с YAML/JSON;
- Меньший размер, проще кеширование и распространение;
- Более стабильная производительность при высоких нагрузках.

#### Поток сессии
1. Входящее событие (вход/команда/нагрузка)
2. Обновление состояния
3. Применение правил профиля (YAML/SQLite)
4. Генерация ответа (с реалистичным временем)
5. Логгирование + извлечение IOC

#### Логи и IOC
Фиксируются структурированные события: IP/ID сессии, попытки входа, команды/нагрузки, время и результаты. На их основе извлекаются **IOC**, классифицируются атаки, а алерты экспортируются в системы SOC.

---

### Создатели

Этот хонипот был создан **tanhiowyatt** и **koshanzov**. Наше первоначальное сотрудничество над продвинутыми прототипами хонипотов переросло в текущий open-source проект в области кибербезопасности, ориентированный на реалистичную симуляцию угроз, классификацию атак с использованием ML и бесшовную интеграцию с SOC.

---

### Отказ от ответственности

Это программное обеспечение предназначено только для образовательных и исследовательских целей. Запуск хонипота сопряжен со значительными рисками. Автор не несет ответственности за любой ущерб или неправомерное использование.

---

<p align="center">
  <i>Revision: 1.0 - April 2026 - Cyanide Honeypot</i>
</p>
