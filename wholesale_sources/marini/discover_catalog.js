function discoverMariniCatalog() {
  const links = [...document.querySelectorAll("a")].map(linkData);
  const categories = links.filter(isCatalogCategory).map(categoryData);
  return {
    url: location.href,
    loggedIn: Boolean(document.querySelector("input[name='searchPhrase']")),
    searchInputSelector: "input[name='searchPhrase']",
    categoryLinkSelector: "a[href*='/items/'][href*='parent=0']",
    rootCatalogRoute: "/items/0",
    searchRoutePattern: "/items/0?searchPhrase={query}&sortMode=Accuracy",
    categoryCount: categories.length,
    sampleCategories: categories.slice(0, 20),
    bibsCategory: categories.find(item => item.text === "BIBS") || null,
  };
}

function linkData(anchor) {
  return {
    text: cleanText(anchor.innerText),
    href: anchor.href,
  };
}

function categoryData(link) {
  return {
    text: link.text,
    route: new URL(link.href).pathname + new URL(link.href).search,
  };
}

function isCatalogCategory(link) {
  return link.text && link.href.includes("/items/");
}

function cleanText(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}
