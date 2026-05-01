from shopify_store.core.credentials import load_shopify_access
from shopify_store.core.paths import project_root_from


def load_shopify_credentials():
    try:
        return load_shopify_access(project_root_from(__file__))
    except RuntimeError:
        return None
