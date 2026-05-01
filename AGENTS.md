# AGENTS.md - MamaPack

## Базовые Правила
- Код: 5-300-20-3: не больше 5 параметров, 300 строк на файл, 20 строк на метод, 3 уровней вложенности.
- Один класс/компонент - один файл.
- Архитектура feature-based: каждая фича в своей папке.
- Не создавай тесты, новые инструкции и `.md` файлы без просьбы пользователя.
- Для библиотек/API/setup используй Context7, если доступен.

## Карта Проекта
- `wholesale_sources/<source>`: только поставщик - логин, каталог, XML/API/detail-page, парсинг, raw supplier-артефакты. Без Shopify.
- `pipelines/<source>_to_shopify`: рабочие сценарии поставщик -> Shopify/BaseLinker, планы и отчеты загрузки.
- `shopify_store`: общий Shopify-код - credentials, GraphQL, products, media, collections, reusable операции.
- `shopify_store/seo`: SEO export/apply/backup, правила `handle`, `seo.title`, `seo.description`.
- `store_reports`: внешние аудиты и отчеты, не рабочий код.
- `documents`: инвойсы, XLSX/PDF и исходные документы.

## Куда Идти По Задаче
- Получить/распарсить данные поставщика: `wholesale_sources/<source>`.
- Загрузить товары из поставщика: `pipelines/<source>_to_shopify`.
- Изменить создание товара, SKU, media, collections: `shopify_store/products`, `shopify_store/media`, `shopify_store/collections`.
- Изменить SEO магазина: `shopify_store/seo`.
- AIK/AICO текущий импорт: `pipelines/aik_to_shopify/main.py`.
- Marini Tega wanienki: `pipelines/marini_to_shopify/*.ps1`.

## Как Добавлять Новое
- Новый поставщик: создать `wholesale_sources/<source>` для сбора данных и `pipelines/<source>_to_shopify` для загрузки.
- Новый Shopify-функционал: reusable API-код в `shopify_store`, сценарий запуска в `pipelines` или `shopify_store/seo/scripts`.
- Новый SEO-алгоритм: менять маленькие файлы в `shopify_store/seo/*_rules.py`, не плодить второй export-скрипт.
- Не добавлять старые CSV/manual/import режимы рядом с актуальным пайплайном.
- Расширять текущий поток, а не создавать параллельную реализацию.

## Shopify Правила
- Использовать установленное Admin API приложение; не запускать установку нового приложения через Shopify CLI.
- Доступ брать из `key.md` или env: `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ADMIN_TOKEN`, `SHOPIFY_API_VERSION`; секреты не выводить.
- Новые B2B-товары создавать `DRAFT`.
- Перед созданием проверять уникальность SKU; при конфликте добавлять дефис и цифры.
- Товары без фото не загружать, если пользователь явно не разрешил.
- Фото можно передавать через `originalSource`; после загрузки проверять `media READY`.
- Для Marini наличие проверять по `In Stock: N`, грузить только если `N > 0`.
- Польские title/description/SEO писать с польскими буквами; handle делать латиницей, lower-case, с дефисами.

## Перед Финалом
- Проверить существующие пути через `rg --files`.
- После правок проверить импорты/PowerShell parse по затронутым зонам.
- Удалить `__pycache__`.
- Не откатывать чужие изменения.
