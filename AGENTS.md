# AGENTS.md - MamaPack


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
- Для карточек с вариантами, когда в названии поставщика есть серийные артикулы/коды, общее название товара писать в формате `BRAND BASE_CODE(extra_codes) - Название товара`, где `BASE_CODE` - первый код полностью, а в скобках только отличающиеся окончания следующих кодов. Примеры: `AKUKU A0517(18) - Śliniak z rękawkiem`, `AKUKU A0549(50, 51, 52) - Majtki jednorazowe poporodowe - (5 szt.)`, `CANPOL 73/001(2) - Wielorazowe majtki poporodowe - SIATECZKOWE - (2szt.)`. Варианты при этом называть только отличающим признаком, без повторения общего названия.
- Перед созданием проверять уникальность SKU внутри новой партии и в Shopify; не создавать товары/варианты с повторяющимся SKU. Если SKU должен остаться поставщицким один-в-один, конфликт выносить в отчет или уточнять у пользователя, а не менять SKU молча.
- При переводе товара из `DRAFT` в `ACTIVE` менять статус через `productChangeStatus`, затем публиковать товар через `publishablePublish` во все стандартные каналы продаж магазина: `Online Store` (`gid://shopify/Publication/188743745869`), `Shop` (`gid://shopify/Publication/288666517837`) и `Google & YouTube` (`gid://shopify/Publication/279484531021`). После изменения сверять, что статус `ACTIVE` и товар опубликован в этих publications.
- Канал `Google & YouTube` связан с Google Merchant Center и нужен для показа товара в Google, но публикация в этот канал может автоматически включить paid Google Ads. После активации/публикации товара дождаться появления всех offer/SKU этого Shopify-товара в Merchant Center и сразу поставить paid ads на паузу именно для этих offer/SKU, если пользователь явно не просил оставить платную рекламу включенной.
- Shopify API показывает только публикацию в канал `Google & YouTube`; он не подтверждает, участвует ли товар в paid Google Ads. Для такой проверки использовать Content API for Shopping `shoppingcontent.googleapis.com/content/v2.1` с аккаунтом Merchant Center `5548494754` и ключом `MerchantKEY.json` из корня проекта. Ключ не выводить и не коммитить.
- Для паузы paid ads в Merchant Center использовать Content API `products.update`: `PATCH /content/v2.1/5548494754/products/{productId}?updateMask=pause` с body `{"pause":"ads"}` для каждого offer/SKU активируемого товара. Это соответствует выключенному флажку `Show in ads`, но оставляет товар опубликованным в Google. После изменения проверять прямым `products.get`, что у каждого offer/SKU `pause = "ads"`; `productstatuses`/`approved` не использовать как признак выключенного Ads-флажка.
- Для активируемых товаров включать учет остатков у каждого варианта (`inventoryItemUpdate` с `tracked: true`) и разрешать продажу в минус (`inventoryPolicy: CONTINUE`). После изменения проверять у всех вариантов `tracked = true` и `inventoryPolicy = CONTINUE`.
- Для проверки/копирования каналов продаж Shopify Admin token должен иметь доступ к publications (`read_publications` для чтения и соответствующий publish/write-доступ для публикации); если scope не хватает, остановиться и сообщить, какой доступ нужен.
- Товары без фото не загружать, если пользователь явно не разрешил.
- Фото можно передавать через `originalSource`; после загрузки проверять `media READY`.
- Для Marini наличие проверять по `In Stock: N`, грузить только если `N > 0`.
- Польские title/description/SEO писать с польскими буквами; handle делать латиницей, lower-case, с дефисами.
- Единый стиль `descriptionHtml` держать только в `shopify_store/products/description_style.py`; поставщики передают факты/структуру, но не хранят свои цвета, сетки и inline-стили.

## Перед Финалом
- Проверить существующие пути через `rg --files`.
- После правок проверить импорты/PowerShell parse по затронутым зонам.
- Удалить `__pycache__`.
- Не откатывать чужие изменения.
