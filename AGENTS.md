# AGENTS.md instructions for c:\Users\User\Desktop\GameWeb\Price

ПРАВИЛО ДЛЯ НАПИСАНЯ КОДА!!!
- Правило 5-300-20-3: ≤5 параметров у функции, ≤300 строк на файл, ≤20 строк на метод, ≤3 уровня вложенности.
- Один класс/компонент — один файл.

ПРАВИЛА ДЛЯ АРХИТЕКТУРЫ!
- Пишем код по принципу feature-based (каждая фича отдельно в папке).

- Не создавай тестов и дополнительных инструкций а также файлов .md если об этом не просит пользователь.

Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

Дополнительная рабочая заметка
- Shopify theme files для этого проекта нужно искать вне текущего репозитория `Price`.
- Сначала проверяй соседнюю папку `C:\Users\User\Desktop\GameWeb\MamaPack`.
- Без явной команды пользователя не вноси правки в `MamaPack` автоматически.

Правила работы с Shopify для MamaPack
- Для Shopify использовать уже установленное Admin API приложение, а не запускать установку нового приложения через Shopify CLI.
- Доступ брать из `key.md` в корне проекта или из переменных `SHOPIFY_STORE_DOMAIN`, `SHOPIFY_ADMIN_TOKEN`, `SHOPIFY_API_VERSION`.
- Секреты из `key.md` никогда не выводить в ответ пользователю и не писать в отчеты.
- Основной магазин: `c1e90d-4.myshopify.com`, API version по умолчанию `2026-04`.
- Для API использовать GraphQL Admin API с заголовком `X-Shopify-Access-Token`.
- Все новые товары из B2B поставщиков создавать только в статусе `DRAFT`, если пользователь явно не сказал иначе.
- Перед созданием товара проверять уникальность SKU в Shopify. Если SKU уже существует, добавить дефис и цифры.
- Товары без фото не загружать, если пользователь явно не разрешил.
- Фото можно передавать в Shopify через `originalSource` по прямой ссылке поставщика. После успешной загрузки обязательно проверить, что media в Shopify имеет статус `READY`; после этого Shopify хранит свою копию на CDN.
- Если поставщик не отдает фото в XML/API/detail-page, товар пропускать и фиксировать SKU в отчете.
- Для Marini наличие товара проверять по строке страницы `In Stock: N`; загружать только если `N > 0`.
- Для Marini рабочий код и отчеты держать в папке `marini_b2b`.
- После массовой загрузки всегда сохранять JSON-отчет с Shopify product IDs, source SKU, final SKU, handle, статусом и пропущенными товарами.
- После загрузки обязательно читать товары обратно из Shopify и проверять: статус `DRAFT`, наличие media, готовность media, коллекции, SKU.
- Для категорий использовать Shopify collections. Если нужна новая категория внутри существующей, создать/найти отдельную коллекцию и добавить товары и в родительскую, и в новую коллекцию.
- Для польского магазина title, descriptionHtml, SEO title и SEO description писать нормальным польским языком с польскими буквами.
- Shopify handle/URL делать латиницей без польских диакритических знаков, в нижнем регистре, с дефисами и SKU в конце для уникальности.
- SEO для Google заполнять отдельно: `handle`, `seo.title`, `seo.description`. SEO title держать примерно до 70 символов, SEO description примерно до 160 символов.
- Описание товара делать в сохраненном стиле MamaPack: аккуратный HTML на польском с блоками hero, intro, `Opis producenta`, benefit-cards, `Najważniejsze informacje`, pielęgnacja/użytkowanie, safety note и короткая source note.
- При генерации описания использовать польское описание поставщика, если оно есть, и исправлять явные опечатки без потери смысла.
- Для PowerShell-скриптов с польскими буквами сохранять файлы как UTF-8 with BOM и отправлять JSON в Shopify как UTF-8 bytes с `charset=utf-8`.
- Если Shopify API вернул userErrors или GraphQL errors, остановиться, исправить payload и не продолжать массовую загрузку вслепую.
