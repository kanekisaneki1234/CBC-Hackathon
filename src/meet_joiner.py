"""
Google Meet meeting automation using Playwright
"""
import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
from .config import Config

logger = logging.getLogger(__name__)


class MeetJoiner:
    """Handles joining Google Meet meetings via browser automation"""

    def __init__(self, display_name: Optional[str] = None):
        self.display_name = display_name or Config.MEET_DISPLAY_NAME
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
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--enable-usermedia-screen-capturing",  # Enable screen/audio capture
                "--auto-select-desktop-capture-source=Entire screen",  # Auto-select capture source
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
        Join a Google Meet meeting

        Args:
            meeting_url: The Google Meet URL (https://meet.google.com/xxx-yyyy-zzz)
            password: Not used for Google Meet (included for API compatibility)

        Returns:
            bool: True if successfully joined
        """
        if not self.page:
            await self.initialize()

        try:
            logger.info(f"Navigating to meeting: {meeting_url}")
            await self.page.goto(meeting_url, wait_until="domcontentloaded")

            # Wait for page to load
            await asyncio.sleep(3)

            # Try to handle "Continue without an account" if we see a sign-in page
            try:
                # Look for guest join option
                guest_selectors = [
                    "text=/continue without.*account/i",
                    "text=/join as a guest/i",
                    "text=/without signing in/i",
                    "button:has-text('Guest')",
                ]

                for selector in guest_selectors:
                    try:
                        guest_link = self.page.locator(selector).first
                        if await guest_link.is_visible(timeout=3000):
                            logger.info("Found guest join option, clicking...")
                            await guest_link.click()
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Guest join option not found or not needed: {e}")

            # Enter display name
            # Google Meet typically has a name input field before joining
            try:
                # Try multiple possible name input selectors
                name_input_selectors = [
                    "input[placeholder*='name' i]",
                    "input[aria-label*='name' i]",
                    "input[type='text']",
                    "input.whsOnd",  # Common Google Meet class for name input
                ]

                name_entered = False
                for selector in name_input_selectors:
                    try:
                        name_input = self.page.locator(selector).first
                        if await name_input.is_visible(timeout=3000):
                            logger.info(f"Entering display name: {self.display_name}")
                            await name_input.click()
                            await name_input.fill("")  # Clear any existing text
                            await name_input.fill(self.display_name)
                            name_entered = True
                            break
                    except:
                        continue

                if not name_entered:
                    logger.warning("Could not find name input field")
            except Exception as e:
                logger.debug(f"Name input handling error: {e}")

            # Disable camera and microphone before joining (optional - keeps it muted)
            try:
                # Look for camera/mic toggle buttons
                await asyncio.sleep(1)

                # Try to turn off camera
                camera_selectors = [
                    "button[aria-label*='camera' i]",
                    "button[aria-label*='video' i]",
                    "div[data-tooltip*='camera' i]",
                ]

                for selector in camera_selectors:
                    try:
                        camera_btn = self.page.locator(selector).first
                        if await camera_btn.is_visible(timeout=2000):
                            # Check if camera is on (might need to turn off)
                            await camera_btn.click()
                            logger.info("Toggled camera")
                            await asyncio.sleep(0.5)
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Camera/mic control error: {e}")

            # Click "Join now" or "Ask to join" button
            try:
                join_button_selectors = [
                    "button:has-text('Join now')",
                    "button:has-text('Ask to join')",
                    "button:has-text('Join')",
                    "button[aria-label*='join' i]",
                    "span:has-text('Join now')",
                    "span:has-text('Ask to join')",
                ]

                join_clicked = False
                for selector in join_button_selectors:
                    try:
                        join_button = self.page.locator(selector).first
                        if await join_button.is_visible(timeout=3000):
                            logger.info(f"Clicking join button: {selector}")
                            await join_button.click()
                            join_clicked = True
                            await asyncio.sleep(3)
                            break
                    except:
                        continue

                if not join_clicked:
                    logger.warning("Could not find join button - may already be in meeting")
            except Exception as e:
                logger.warning(f"Join button click error: {e}")

            # Wait for meeting to load
            await asyncio.sleep(5)

            # If "Ask to join" was clicked, wait for host to admit
            # Check for waiting room indicator
            try:
                waiting_indicators = [
                    "text=/waiting for.*host/i",
                    "text=/asked to join/i",
                ]

                for selector in waiting_indicators:
                    try:
                        waiting_elem = self.page.locator(selector).first
                        if await waiting_elem.is_visible(timeout=2000):
                            logger.info("Waiting for host to admit to meeting...")
                            # Wait up to 60 seconds for admission
                            for _ in range(12):
                                await asyncio.sleep(5)
                                if await self._check_in_meeting():
                                    break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Waiting room check error: {e}")

            # Check if we're in the meeting
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
            # Look for common Google Meet meeting UI elements
            indicators = [
                "button[aria-label*='microphone' i]",
                "button[aria-label*='Turn off microphone' i]",
                "button[aria-label*='Turn on microphone' i]",
                "button[aria-label*='Leave call' i]",
                "button[aria-label*='End call' i]",
                "div[data-meeting-title]",
                "div[data-self-name]",
                "[data-fps-request-screencast-cap]",
            ]

            for indicator in indicators:
                try:
                    element = self.page.locator(indicator).first
                    if await element.is_visible(timeout=2000):
                        logger.debug(f"Found meeting indicator: {indicator}")
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

            # Try to find and click the Leave/End call button
            leave_selectors = [
                "button[aria-label*='Leave call' i]",
                "button[aria-label*='End call' i]",
                "button:has-text('Leave call')",
                "button:has-text('End call')",
            ]

            for selector in leave_selectors:
                try:
                    leave_button = self.page.locator(selector).first
                    if await leave_button.is_visible(timeout=3000):
                        await leave_button.click()
                        logger.info("Clicked leave button")
                        await asyncio.sleep(1)
                        break
                except:
                    continue

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
