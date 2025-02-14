import chromedriver_autoinstaller
from logger import logger

def install_chromedriver():
    """Automatically installs the correct ChromeDriver version."""
    chromedriver_autoinstaller.install()
    logger.info("[console.log] ChromeDriver auto-installed or verified.")
