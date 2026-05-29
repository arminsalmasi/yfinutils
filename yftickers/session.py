import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import threading
import logging
import time

logger = logging.getLogger(__name__)

# Standard browser headers to avoid detection and bot blocking
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://finance.yahoo.com",
    "Referer": "https://finance.yahoo.com/",
}

class YahooSessionManager:
    """
    Thread-safe Singleton to manage optimized requests to Yahoo Finance.
    Maintains a connection-pooled requests.Session, automatic cookie/crumb resolution,
    and retry-backoff configurations for high speed and reliability.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(YahooSessionManager, cls).__new__(cls)
                cls._instance._init_session()
            return cls._instance

    def _init_session(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        
        # Configure connection pooling for heavy concurrency (e.g. bulk downloads)
        # Reuses TCP connections instead of doing full TLS handshakes repeatedly.
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retries
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.cookie_lock = threading.Lock()
        self.crumb = None
        self.cookies = None
        self.last_fetch_time = 0

    def get_cookie_and_crumb(self, force_refresh=False):
        """
        Thread-safe cookie and crumb retrieval with caching.
        Returns a tuple of (cookies, crumb).
        """
        now = time.time()
        # Cache cookie/crumb for 1 hour to prevent excessive calls
        if self.crumb and not force_refresh and (now - self.last_fetch_time < 3600):
            return self.cookies, self.crumb

        with self.cookie_lock:
            # Double-check inside lock
            if self.crumb and not force_refresh and (now - self.last_fetch_time < 3600):
                return self.cookies, self.crumb

            logger.debug("Fetching new Yahoo cookie and crumb")
            try:
                # 1. Fetch cookie by hitting the Yahoo Consent / FC page
                self.session.cookies.clear()
                resp = self.session.get("https://fc.yahoo.com", timeout=10)
                
                # 2. Query Yahoo for the test crumb
                crumb_resp = self.session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=10)
                if crumb_resp.status_code == 200 and crumb_resp.text:
                    self.crumb = crumb_resp.text.strip()
                    self.cookies = self.session.cookies
                    self.last_fetch_time = time.time()
                    logger.debug(f"Successfully retrieved Yahoo crumb: {self.crumb}")
                else:
                    logger.warning(f"Failed to fetch crumb (status: {crumb_resp.status_code})")
            except Exception as e:
                logger.error(f"Failed to retrieve cookie/crumb from Yahoo: {e}")
                # Fallback to no-crumb if error occurs
                if not self.crumb:
                    self.crumb = None
            
            return self.cookies, self.crumb

    def execute_request(self, url, params=None, timeout=15):
        """
        Executes a GET request on Yahoo Finance.
        Handles cookies, crumbs, status checking, and automatic rate-limit backing off.
        """
        if params is None:
            params = {}

        # Retrieve current cached cookie/crumb
        _, crumb = self.get_cookie_and_crumb()
        if crumb:
            params["crumb"] = crumb
        else:
            params.pop("crumb", None)

        # Attempt the request
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
                
                # Handle rate limits (429)
                if resp.status_code == 429:
                    wait_time = 3 ** attempt  # 1s, 3s, 9s back-off
                    logger.warning(f"Rate limited (429). Sleeping for {wait_time}s and retrying...")
                    time.sleep(wait_time)
                    continue
                
                # Handle unauthorized crumb (401)
                if resp.status_code == 401 and attempt == 0:
                    # Crumb might be expired/invalid, try forcing a refresh once
                    logger.warning("Unauthorized (401). Refreshing crumb and retrying...")
                    self.get_cookie_and_crumb(force_refresh=True)
                    if self.crumb:
                        params["crumb"] = self.crumb
                    else:
                        params.pop("crumb", None)
                    continue

                return resp
            except Exception as e:
                if attempt == 2:
                    raise e
                time.sleep(1)

        return resp

# Global instance for standard access
yahoo_session = YahooSessionManager()
