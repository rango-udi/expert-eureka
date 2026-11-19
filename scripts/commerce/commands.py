"""Container-only configuration and native commerce coordination."""

import html
import io
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time

APPS = {"nopcommerce", "prestashop", "woocommerce"}


def environment(app):
    """Create private settings from the selected template without replacing values."""
    if app not in APPS:
        raise ValueError("Unknown commerce adapter.")
    root = Path("/workspace")
    target = root / ".env"
    if target.is_symlink() or (root / ".runtime").is_symlink():
        raise ValueError("Configuration and runtime paths must not be links.")
    if target.exists():
        validate_environment(target.read_text())
        print("Private configuration preserved.")
        return
    if (root / ".runtime/initialized.json").exists():
        raise ValueError("Data exists without .env. Restore the original configuration.")
    template = (root / ".env.template").read_text()
    replacements = {key: secrets.token_hex(24) for key in
                    ("DB_PASSWORD", "DB_ROOT_PASSWORD", "ADMIN_PASSWORD", "CUSTOMER_PASSWORD")}
    for key, value in replacements.items():
        template = re.sub(rf"(?m)^{key}=$", f"{key}={value}", template)
    validate_environment(template)
    with target.open("x", encoding="utf-8") as stream:
        stream.write(template)
    target.chmod(0o600)
    print("Private configuration created from .env.template. Keep it with database backups.")


def validate_environment(text):
    """Reject missing secrets and invalid native URL settings without printing values."""
    settings = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or key in settings or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError("Invalid or duplicate environment entry. Keep one KEY=value per line.")
        settings[key] = value.strip().strip("\"'")
    port = settings.get("HTTP_PORT", "")
    if not port.isdigit() or not 1024 <= int(port) <= 65535:
        raise ValueError("HTTP_PORT must be a numeric port within 1024..65535.")
    for key in ("DB_PASSWORD", "DB_ROOT_PASSWORD", "ADMIN_PASSWORD", "CUSTOMER_PASSWORD"):
        if len(settings.get(key, "")) < 16:
            raise ValueError(key + " must contain at least 16 characters. Preserve original credentials with existing data.")
    for key in ("ADMIN_EMAIL", "CUSTOMER_EMAIL"):
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", settings.get(key, "")):
            raise ValueError(key + " must contain an email address.")
    if settings["ADMIN_EMAIL"].casefold() == settings["CUSTOMER_EMAIL"].casefold():
        raise ValueError("Administrator and customer emails must differ.")


def records(app):
    """Validate the shared source before returning native adapter input."""
    from fuzcake_data import reference, validate
    validate(app)
    return reference("catalogue")


def token(response):
    """Extract an ASP.NET antiforgery token without logging its value."""
    from html.parser import HTMLParser

    class FormParser(HTMLParser):
        """Read input fields regardless of HTML attribute order."""

        def handle_starttag(self, tag, attrs):
            """Remember the hidden token used by the native application."""
            values = dict(attrs)
            if tag == "input" and values.get("name") == "__RequestVerificationToken":
                self.value = values.get("value", "")

    parser = FormParser()
    parser.value = ""
    parser.feed(response.text)
    if not parser.value:
        raise ValueError("The native page did not provide an antiforgery token. Review the app logs.")
    return parser.value


def nop_init():
    """Install nopCommerce and import only absent SKUs through its native admin API."""
    import requests
    from openpyxl import Workbook
    catalogue = records("nopcommerce")
    session = requests.Session()
    base = "http://app:" + os.environ["HTTP_PORT"]
    deadline = time.monotonic() + 300
    while True:
        try:
            response = session.get(base + "/", timeout=10)
            response.raise_for_status()
            break
        except requests.RequestException:
            if time.monotonic() >= deadline:
                raise ValueError("nopCommerce did not answer within 300 seconds. Inspect app and database logs.")
            time.sleep(2)
    if "/install" in response.url.lower():
        response = session.post(base + "/Install", data={
            "__RequestVerificationToken": token(response),
            "AdminEmail": os.environ["ADMIN_EMAIL"],
            "AdminPassword": os.environ["ADMIN_PASSWORD"],
            "ConfirmPassword": os.environ["ADMIN_PASSWORD"],
            "DataProvider": "PostgreSQL", "ServerName": "db", "DatabaseName": "commerce",
            "Username": "commerce", "Password": os.environ["DB_PASSWORD"],
            "CreateDatabaseIfNotExists": "false", "InstallSampleData": "false",
            "InstallRegionalResources": "false", "SubscribeNewsletters": "false",
            "Country": "US", "ConnectionStringRaw": "false",
        }, timeout=600)
        response.raise_for_status()
        # The native installation view performs this AJAX request in a browser.
        try:
            restarted = session.get(base + "/install/restartapplication", timeout=30)
            restarted.raise_for_status()
        except requests.ConnectionError:
            # A closing response is expected when the native host restarts itself.
            pass
        # The installer writes settings and redirects the next request through restart.
        for attempt in range(90):
            try:
                ready = session.get(base + "/login", timeout=10)
                if ready.ok and "/install" not in ready.url.lower():
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        else:
            raise ValueError("Native installation did not complete. Keep .env and inspect logs before retrying.")
    login = session.get(base + "/login", timeout=30)
    login.raise_for_status()
    signed = session.post(base + "/login", data={
        "__RequestVerificationToken": token(login), "Email": os.environ["ADMIN_EMAIL"],
        "Password": os.environ["ADMIN_PASSWORD"], "RememberMe": "false",
    }, timeout=30)
    signed.raise_for_status()
    page = session.get(base + "/Admin/Product/List", timeout=30)
    page.raise_for_status()
    if "/login" in page.url.lower() or "/install" in page.url.lower():
        raise ValueError("Administrator login failed. Restore the original .env; passwords were not reset.")
    csrf = token(page)
    configure_nop_store(session, base)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Products"
    headers = ["ProductType", "Name", "Sku", "ShortDescription", "FullDescription", "Published",
               "VisibleIndividually", "ProductTemplateId", "Price", "StockQuantity", "ManageInventoryMethod",
               "OrderMinimumQuantity", "OrderMaximumQuantity", "Categories", "Picture1", "ShowOnHomepage"]
    sheet.append(headers)
    missing = []
    categories = {item["id"]: item["name"] for item in catalogue["categories"]}
    for product in catalogue["products"]:
        result = session.post(base + "/Admin/Product/ProductList", data={
            "__RequestVerificationToken": csrf, "SearchProductName": product["sku"],
            "SearchPublishedId": "0", "Start": "0", "Length": "100", "Draw": "1", "PageSize": "100", "Page": "1",
        }, timeout=30)
        result.raise_for_status()
        existing = result.json().get("Data")
        if not isinstance(existing, list):
            raise ValueError("Product lookup returned an unexpected response. Import stopped to preserve existing data.")
        if any(item.get("Sku") == product["sku"] for item in existing):
            continue
        missing.append(product["sku"])
        sheet.append([5, product["name"], product["sku"], product["description"],
                      html.escape(product["description"] + " " + product["size"]), True,
                      True, 1, float(product["price"]), product["stock"], 1, 1, 100,
                      categories[product["category"]], "/fuzcake-data/assets/" + product["image"], True])
    if missing:
        output = io.BytesIO()
        workbook.save(output)
        imported = session.post(base + "/Admin/Product/ImportExcel", data={
            "__RequestVerificationToken": csrf}, files={"importexcelfile": (
                "fuzcake-catalogue.xlsx", output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, timeout=300)
        imported.raise_for_status()
        for sku in missing:
            result = session.post(base + "/Admin/Product/ProductList", data={
                "__RequestVerificationToken": csrf, "SearchProductName": sku,
                "SearchPublishedId": "0", "Start": "0", "Length": "100", "Draw": "1", "PageSize": "100", "Page": "1"}, timeout=30)
            result.raise_for_status()
            if not any(row.get("Sku") == sku for row in result.json().get("Data", [])):
                raise ValueError("The native importer did not confirm every SKU. Review admin notifications; rerun setup to add missing products.")
    print(f"nopCommerce catalogue verified; {len(missing)} missing products imported.")


def configure_nop_store(session, base):
    """Replace the native installer store placeholder while preserving operator edits."""
    from html.parser import HTMLParser
    from fuzcake_data import reference

    class StoreForm(HTMLParser):
        """Read the native store edit form without evaluating page scripts."""

        def handle_starttag(self, tag, attrs):
            """Collect submitted input fields and the original store name."""
            item = dict(attrs)
            if tag != "input" or not item.get("name"):
                return
            if item.get("type") in ("submit", "button", "file"):
                return
            if item.get("type") in ("checkbox", "radio") and "checked" not in item:
                return
            self.fields[item["name"]] = item.get("value", "")

    response = session.get(base + "/Admin/Store/Edit/1", timeout=30)
    response.raise_for_status()
    form = StoreForm()
    form.fields = {}
    form.feed(response.text)
    if form.fields.get("Name") != "Your store name":
        return
    store = reference("store")
    address = store["addresses"][0]
    form.fields.update({"Name": store["name"], "CompanyName": address["name"],
                        "Url": "http://127.0.0.1:" + os.environ["HTTP_PORT"] + "/",
                        "CompanyAddress": address["street"] + ", " + address["city"],
                        "CompanyPhoneNumber": store["phone"], "save": "save"})
    response = session.post(base + "/Admin/Store/Edit/1", data=form.fields, timeout=30)
    response.raise_for_status()
    confirmed = session.get(base + "/Admin/Store/Edit/1", timeout=30)
    confirmed.raise_for_status()
    form.fields = {}
    form.feed(confirmed.text)
    if form.fields.get("Name") != store["name"]:
        raise ValueError("Native store identity was not saved. Review the store edit form in administration.")


def complete(app):
    """Write a readiness marker only after the native initializer succeeded."""
    runtime = Path("/workspace/.runtime")
    runtime.mkdir(exist_ok=True)
    marker = runtime / "initialized.json"
    if marker.is_symlink():
        raise ValueError("The initialization marker must not be a link.")
    marker.write_text(json.dumps({"app": app, "schema_version": 1}) + "\n")


def main():
    """Dispatch a bounded maintenance task without exposing native exception details."""
    command, app = sys.argv[1:3]
    if app not in APPS:
        raise ValueError("Unknown commerce adapter.")
    if command == "env":
        environment(app)
    elif command == "validate":
        validate_environment(Path("/workspace/.env").read_text())
        records(app)
        print("Shared records and asset checksums are valid.")
    elif command == "init" and app == "nopcommerce":
        nop_init()
    elif command == "complete":
        complete(app)
    else:
        raise ValueError("Unsupported maintenance task.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Exception strings from HTTP/DB clients can contain private settings.
        print("ERROR: Commerce maintenance failed (" + type(error).__name__ + "). Keep .env and data; inspect the selected app logs. No credentials were printed.", file=sys.stderr)
        if isinstance(error, ValueError):
            print("ERROR: " + str(error), file=sys.stderr)
        raise SystemExit(1)
