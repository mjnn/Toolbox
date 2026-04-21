"""Chrome + ChromeDriver wiring: prefer Selenium Manager (matches installed Chrome), optional env override."""
from __future__ import annotations

import os
from pathlib import Path

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service


def chrome_options_headless_legacy() -> ChromeOptions:
    """Headless + relax cert checks for internal HTTPS portals (legacy scripts use verify=False on requests)."""
    opts = ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--ignore-certificate-errors")
    opts.add_argument("--allow-insecure-localhost")
    return opts


def chrome_driver_service() -> Service:
    """
    - CHROME_DRIVER_PATH / WEBDRIVER_CHROME_DRIVER: explicit chromedriver (e.g. intranet offline bundle).
    - Otherwise: Service() so Selenium 4.6+ resolves a driver matching the installed Chrome.
    """
    for key in ("CHROME_DRIVER_PATH", "WEBDRIVER_CHROME_DRIVER"):
        override = (os.environ.get(key) or "").strip()
        if override and Path(override).is_file():
            return Service(executable_path=override)
    return Service()
