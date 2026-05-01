# SEO-План Приоритетов Для mamapack.pl

Дата: 2026-04-15

Основа документа:
- проверены все `330` URL из `sitemap.xml` как `Googlebot`
- сверены `robots.txt`, sitemap, HTML, `title`, `meta description`, `canonical`, `H1`, JSON-LD
- отдельно проверены официальные материалы Shopify по SEO и требованиям к темам

Важно:
- ниже проблемы отсортированы от самых критичных для SEO сайта к менее критичным
- если проблема решается только в админке Shopify, это отмечено отдельно
- если проблема требует правки темы, это тоже отмечено отдельно
- отсутствие `hreflang` здесь не считаю проблемой, потому что магазин выглядит как одноязычный `pl`

## 1. В индексе есть мусорные и дублирующие product URL

Что не так:

В индексе и sitemap есть отдельные товарные URL, которые выглядят как технические или дублирующие:
- `8` URL с `copy`
- `11` URL с суффиксами `-1`, `-2`, `-3`

Это не просто косметика. Такие страницы размывают релевантность, создают каннибализацию, дублируют сниппеты и забирают crawl budget.

Где находится:

Только в `products`.

Примеры:
- `https://mamapack.pl/products/bibs-50171216-butelka-silikon-sredni-przeplyw-270-ml-kosc-sloniowa-copy`
- `https://mamapack.pl/products/rozek-niemowlecy-muslinowy-75x75-cm-z-kokarda-bawelna-copy`
- `https://mamapack.pl/products/torba-do-szpitala-1`
- `https://mamapack.pl/products/torba-do-szpitala-2`
- `https://mamapack.pl/products/klapki-damskie-bialy-1`

Как лечить:

Если это реальные дубли:
- удалить дубли из канала `Online Store`
- либо удалить товары полностью
- поставить `URL redirect` со старого URL на основной товар
- убрать дубли из меню, подборок и внутренних ссылок

Если это не дубли, а отдельные товары:
- дать каждому нормальный уникальный handle
- переписать title, description и контент, чтобы страницы не конкурировали между собой

Ответственный:

Главным образом `админка Shopify`.

Почему это приоритет №1:

Пока в индексе живут дублирующие товарные URL, все последующие SEO-правки работают хуже.

## 2. На части страниц сломана структура H1

Что не так:

Найдено:
- `58` URL без `H1`
- `15` URL с несколькими `H1`

Это уже проблема HTML-шаблонов и частично контента. Для Google это означает неустойчивую структуру документа и слабый главный заголовок страницы.

Где находится:

Наиболее заметно в:
- главной странице
- product templates
- части collection templates
- единично в blog

Примеры без `H1`:
- `https://mamapack.pl/`
- `https://mamapack.pl/products/linomag-puder-100g-hig-kosm-dla-dzieci-i-niemowlat-k056`
- `https://mamapack.pl/products/canpol-1-658-suche-chusteczki-bambusowe-dla-niemowlat-100-szt`

Примеры с несколькими `H1`:
- `https://mamapack.pl/products/me-figi-l-bialy`
- `https://mamapack.pl/products/akuku-a0307-szczotka-i-grzebien-z-naturalnym-wlosiem-biala`
- `https://mamapack.pl/products/szlafrok-damski-z-delikatnego-muslinu-l-wiazany-doctor-nap`

Как лечить:

В теме:
- оставить ровно один контентный `H1` на страницу
- убрать `H1` из логотипа в header
- убрать дубли title-блоков в product template
- не выводить дополнительные блоки с классами вида `h1`, если они дублируют товарный заголовок

В админке:
- почистить описания товаров от вставленных `<h1>`, `<h2>` и маркетплейсного HTML
- особенно там, где второй или третий `H1` приезжает из `description`

Ответственный:

`тема + админка`.

Почему это приоритет №2:

Это системная проблема шаблонов. Она влияет сразу на десятки карточек и на главную.

## 3. На части товаров отсутствует или ломается Product schema

Что не так:

По итоговому crawl:
- `108` product URL не отдали стабильную `Product` schema
- на части URL была только `Organization`
- на части URL schema вообще не нашлась

Это мешает rich results и ухудшает понимание товара поисковиком.

Где находится:

Только в `products`.

Примеры:
- `https://mamapack.pl/products/horizon-majtki-poporodowe-siatka-38-40-a-2szt`
- `https://mamapack.pl/products/linomag-puder-100g-hig-kosm-dla-dzieci-i-niemowlat-k056`
- `https://mamapack.pl/products/bamboolove-pieluszki-jednorazowe-r-xs-27szt`
- `https://mamapack.pl/products/nivea-baby-80571-chusteczki-toddies-a57`

Как лечить:

В теме:
- вынести JSON-LD товара в один стабильный snippet
- выводить его на всех product pages без исключений
- включить минимум:
  - `@type: Product`
  - `name`
  - `description`
  - `image`
  - `sku`
  - `brand`
  - `offers`
  - `price`
  - `priceCurrency`
  - `availability`
  - `url`

Дополнительно:
- проверить, не ломается ли schema на товарах с особыми шаблонами
- проверить, не завязана ли schema на блок, который иногда выключен

Ответственный:

`тема`.

Почему это приоритет №3:

Это не влияет на индекс сильнее, чем дубли URL и сломанный `H1`, но прямо влияет на rich snippets и качество товарной выдачи.

## 4. Meta description массово слишком длинные

Что не так:

Найдено `247` URL с description длиннее `160` символов.

На практике это означает, что Google:
- часто обрежет description
- часто перепишет snippet сам
- хуже удержит целевой коммерческий посыл

Где находится:

Проблема массовая:
- главная
- почти все product pages
- часть collections
- почти все article pages

Примеры:
- главная: `304` символа
- многие product pages: `240-320` символов
- многие blog articles: `320` символов

Как лечить:

В админке:
- у приоритетных страниц переписать description вручную

В теме:
- если поле пустое или тема делает fallback, ограничить вывод до `140-155` символов
- не тянуть в meta description длинный кусок product/article content без обрезки

Рекомендуемый формат:
- 1 основная ключевая фраза
- 1 выгода
- 1 уточнение по товару/категории

Ответственный:

`админка + тема`.

Почему это приоритет №4:

Проблема массовая и влияет на snippet почти по всему сайту, но все же менее критична, чем индексные дубли и шаблонные ошибки структуры.

## 5. Title массово слишком длинные

Что не так:

Найдено `195` URL с title длиннее `65` символов.

Где находится:

Чаще всего:
- главная
- product pages
- часть article pages

Примеры:
- `https://mamapack.pl/`
- `https://mamapack.pl/products/chicco-916600-chusteczki-do-pielegnacji-piersi-72szt`
- `https://mamapack.pl/products/bamboolove-pieluszki-jednorazowe-r-xs-27szt`

Как лечить:

В админке:
- у денежных страниц задать короткие коммерческие title вручную

В теме:
- если title строится автоматически, сократить fallback-логику
- убрать лишние повторения характеристик
- оставлять бренд сайта в конце только если это не раздувает длину сверх нормы

Цель:
- держать `title` в диапазоне `50-65` символов

Ответственный:

`админка + тема`.

Почему это приоритет №5:

Проблема важная, но она слабее, чем индексный мусор, H1 и schema.

## 6. На части важных страниц нет meta description вообще

Что не так:

Найдено `6` URL без `meta description`.

Где находится:

- `https://mamapack.pl/pages/contact`
- `https://mamapack.pl/collections/forbaby`
- `https://mamapack.pl/collections/formam`
- `https://mamapack.pl/collections/zabawa-i-edukacja`
- `https://mamapack.pl/blogs/news`
- `https://mamapack.pl/blogs/przydatne-artykuly`

Как лечить:

В админке:
- заполнить Search engine listing preview

Если часть этих страниц не имеет отдельного SEO-поля:
- добавить fallback в теме через `page_description`
- если `page_description` пустой, собирать короткий description из intro/description шаблона

Ответственный:

Сначала `админка`, при необходимости `тема`.

Почему это приоритет №6:

Проблема точечная, а не системная. Исправляется быстро, но все равно стоит сделать.

## 7. Главная страница слабо оформлена как SEO-лендинг

Что не так:

На главной:
- нет нормального контентного `H1`
- `title` слишком длинный
- `description` слишком длинный

При этом главная обычно является самым сильным URL домена и должна быть максимально чистой.

Где находится:

- `https://mamapack.pl/`

Как лечить:

В теме:
- добавить один явный `H1` в hero или первый текстовый блок
- не использовать логотип в header как основной смысловой заголовок страницы

В админке:
- сократить homepage title
- сократить homepage description

Ответственный:

`тема + админка`.

Почему это приоритет №7:

Это важная точечная проблема, но не настолько системная, как дубли product URL или массовые ошибки product templates.

## 8. У части collection и blog index страниц слишком общий SEO-слой

Что не так:

На части collection/blog index страниц SEO выглядит слишком базово:
- только `Organization` schema
- пустой description
- местами общий title без коммерческого намерения

Где находится:

В основном:
- collection index pages
- blog index pages

Как лечить:

В админке:
- заполнить title и description для коллекций и блогов

В теме:
- обеспечить стабильный `H1` на collection/blog templates
- при необходимости добавить простую разметку хлебных крошек

Ответственный:

`админка`, потом `тема`.

Почему это приоритет №8:

Это уже улучшение второго эшелона, после исправления ядра product SEO.

## Что править сначала

Если делать по очереди, порядок должен быть таким:

1. убрать из индекса дублирующие `copy` и `-1/-2/-3` product URL
2. починить `H1`-логику главной и product templates
3. стабилизировать `Product` schema на всех товарах
4. сократить длинные `meta description`
5. сократить длинные `title`
6. заполнить пустые descriptions
7. доработать главную как SEO-лендинг

## Что можно сделать без разработчика

- удалить или скрыть дублирующие товары
- поставить redirects
- заполнить SEO title и description
- убрать мусорный HTML из product descriptions

## Что почти наверняка требует правки темы

- один правильный `H1` на страницу
- отсутствие дублирующих `H1`
- корректный `Product` JSON-LD на всех product pages
- fallback-логика `title` и `meta description`
- нормальный `H1` на главной

## Подтверждение по Shopify

Shopify прямо разделяет SEO на данные из админки и вывод этих данных темой:

- SEO metadata в теме:  
  https://shopify.dev/docs/storefronts/themes/seo/metadata

- требования к теме и rich product snippets:  
  https://shopify.dev/docs/storefronts/themes/store/requirements

- редактирование SEO в админке:  
  https://help.shopify.com/en/manual/promoting-marketing/seo/adding-keywords

- redirects в админке:  
  https://help.shopify.com/en/manual/online-store/menus-and-links/url-redirect
