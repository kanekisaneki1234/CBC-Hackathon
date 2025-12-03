"""
Zoom meeting automation using Playwright
"""
import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
from .config import Config

logger = logging.getLogger(__name__)


class ZoomJoiner:
    """Handles joining Zoom meetings via browser automation"""

    def __init__(self, display_name: Optional[str] = None):
        self.display_name = display_name or Config.ZOOM_DISPLAY_NAME
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._is_in_meeting = False

    async def initialize(self):
        """Initialize Playwright browser"""
        logger.info("Initializing browser...")
        self.playwright = await async_playwright().start()

        # Launch browser with audio capture capabilities
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Run in headed mode to see the meeting
            args=[
                "--use-fake-ui-for-media-stream",  # Auto-grant media permissions
                "--use-fake-device-for-media-stream",  # Use fake audio device
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # Create context with audio permissions
        context = await self.browser.new_context(
            permissions=["microphone", "camera"],
            viewport={"width": 1280, "height": 720},
        )

        self.page = await context.new_page()
        logger.info("Browser initialized successfully")

    async def join_meeting(self, meeting_url: str, password: Optional[str] = None) -> bool:
        """
        Join a Zoom meeting

        Args:
            meeting_url: The Zoom meeting URL
            password: Optional meeting password

        Returns:
            bool: True if successfully joined
        """
        if not self.page:
            await self.initialize()

        try:
            logger.info(f"Navigating to meeting: {meeting_url}")
            await self.page.goto(meeting_url, wait_until="networkidle")

            # Wait a bit for the page to load
            await asyncio.sleep(2)

            # Click "Join from Your Browser" link if present
            try:
                join_browser_link = self.page.locator("a[class*='join']").first
                if await join_browser_link.is_visible(timeout=5000):
                    logger.info("Clicking 'Join from Browser'...")
                    await join_browser_link.click()
                    await asyncio.sleep(2)
            except Exception as e:
                logger.debug(f"Join from browser link not found or not needed: {e}")

            # Enter display name
            try:
                name_input = self.page.locator("input[type='text']").first
                if await name_input.is_visible(timeout=5000):
                    logger.info(f"Entering display name: {self.display_name}")
                    await name_input.fill(self.display_name)
            except Exception as e:
                logger.debug(f"Name input not found: {e}")

            # Handle password if required
            if password:
                try:
                    password_input = self.page.locator("input[type='password']").first
                    if await password_input.is_visible(timeout=5000):
                        logger.info("Entering meeting password...")
                        await password_input.fill(password)
                except Exception as e:
                    logger.debug(f"Password input not found: {e}")

            # Click join button
            try:
                join_button = self.page.locator("button").filter(has_text="Join")
                if await join_button.is_visible(timeout=5000):
                    logger.info("Clicking Join button...")
                    await join_button.click()
                    await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Join button not found: {e}")

            # Check if we're in the meeting
            await asyncio.sleep(5)

            # Look for indicators that we're in a meeting
            in_meeting = await self._check_in_meeting()

            if in_meeting:
                self._is_in_meeting = True
                logger.info("Successfully joined the meeting!")
                return True
            else:
                logger.warning("Might not have joined successfully - please verify")
                return False

        except Exception as e:
            logger.error(f"Error joining meeting: {e}")
            return False

    async def _check_in_meeting(self) -> bool:
        """Check if we're currently in a meeting"""
        try:
            # Look for common meeting UI elements
            indicators = [
                "button[aria-label*='Mute']",
                "button[aria-label*='Stop Video']",
                "button[aria-label*='Leave']",
                ".meeting-client-inner",
            ]

            for indicator in indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible(timeout=2000):
                        return True
                except:
                    continue

            return False
        except Exception as e:
            logger.debug(f"Error checking meeting status: {e}")
            return False

    async def leave_meeting(self):
        """Leave the current meeting"""
        if not self._is_in_meeting:
            return

        try:
            logger.info("Attempting to leave meeting...")

            # Try to find and click the Leave button
            leave_button = self.page.locator("button").filter(has_text="Leave")
            if await leave_button.is_visible(timeout=5000):
                await leave_button.click()
                await asyncio.sleep(1)

                # Confirm leaving if prompted
                confirm_button = self.page.locator("button").filter(has_text="Leave Meeting")
                if await confirm_button.is_visible(timeout=3000):
                    await confirm_button.click()

            self._is_in_meeting = False
            logger.info("Left the meeting")

        except Exception as e:
            logger.warning(f"Error leaving meeting: {e}")

    async def close(self):
        """Close browser and cleanup"""
        try:
            if self._is_in_meeting:
                await self.leave_meeting()

            if self.browser:
                await self.browser.close()

            if self.playwright:
                await self.playwright.stop()

            logger.info("Browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    @property
    def is_in_meeting(self) -> bool:
        """Check if currently in a meeting"""
        return self._is_in_meeting
