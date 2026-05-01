# MamaPack Agent Project Plan

Коротко: проект хранит инструменты для получения товаров от B2B-поставщиков, подготовки данных и работы с Shopify MamaPack.

## Карта
- `wholesale_sources/<source>`: только входные данные поставщика, логин, каталог, XML/API/detail-page, парсинг supplier-моделей.
- `pipelines/<source>_to_shopify`: рабочие сценарии, которые соединяют поставщика с Shopify/BaseLinker.
- `shopify_store`: общий код Shopify: credentials, GraphQL, products, media, collections, SEO.
- `shopify_store/seo`: SEO export/apply/backup и правила handle/title/description.
- `store_reports`: внешние SEO/аудит-отчеты, не рабочий код.
- `documents`: исходные документы, инвойсы, сопоставления.

## Актуальные Потоки
- AIK/AICO import: `pipelines/aik_to_shopify/main.py`.
- Marini Tega wanienki: `pipelines/marini_to_shopify/*.ps1`.
- Shopify SEO: `shopify_store/seo/scripts/shopify_seo_export.py`, `shopify_apply_recommendations.py`, `shopify_backup_store.py`.

## Границы
- Не создавать второй CSV/manual/import режим рядом с актуальным пайплайном.
- Supplier-код не должен импортировать `shopify_store`.
- `shopify_store` не должен знать про конкретные Marini/AIK страницы.
- Склейка supplier + Shopify живет только в `pipelines`.
- Товары без фото не загружать, кроме явной команды пользователя.
- Новые B2B товары по умолчанию создавать как `DRAFT`.

## Как Дополнять
- Новый поставщик: добавить `wholesale_sources/<source>` для сбора данных и `pipelines/<source>_to_shopify` для загрузки.
- Новая Shopify-операция: добавить reusable код в `shopify_store/<feature>`, а сценарий запуска в pipeline или `shopify_store/seo/scripts`.
- Новое SEO-правило: менять маленькие файлы в `shopify_store/seo/*_rules.py`, не дублировать export-скрипты.
- Новый отчет: сохранять в папку той фичи, которая его создает, или в `store_reports`, если это внешний аудит.

## Перед Изменениями
- Читать `AGENTS.md` и этот файл.
- Проверить существующий путь через `rg --files`.
- Расширять текущий поток, а не добавлять параллельный старый режим.
- После правок проверить импорты/парсинг и удалить `__pycache__`.
