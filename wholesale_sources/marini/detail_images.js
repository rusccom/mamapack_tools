function collectMariniDetailPage() {
  return {
    url: location.href,
    title: firstText(["h1", "h2", ".product-title", ".article-name"]),
    text: cleanText(document.body.innerText).slice(0, 6000),
    images: collectImages(),
    backgrounds: collectBackgrounds(),
    links: collectLinks(),
  };
}

function collectImages() {
  return [...document.images].map(imageData).filter(item => item.src);
}

function imageData(image) {
  return {
    src: image.currentSrc || image.src || "",
    alt: image.alt || "",
    width: image.naturalWidth || image.width || 0,
    height: image.naturalHeight || image.height || 0,
    className: image.className || "",
  };
}

function collectBackgrounds() {
  return [...document.querySelectorAll("*")]
    .map(backgroundData)
    .filter(Boolean);
}

function backgroundData(node) {
  const value = getComputedStyle(node).backgroundImage || "";
  if (!value.includes("url(")) return null;
  return {
    tag: node.tagName.toLowerCase(),
    className: node.className || "",
    value,
  };
}

function collectLinks() {
  return [...document.querySelectorAll("a[href]")]
    .map(link => ({ text: cleanText(link.innerText), href: link.href }))
    .filter(item => item.href && isImageLike(item.href));
}

function isImageLike(value) {
  return /\.(jpe?g|png|webp|gif)(\?|$)/i.test(value);
}

function firstText(selectors) {
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (node && cleanText(node.innerText)) return cleanText(node.innerText);
  }
  return "";
}

function cleanText(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}
