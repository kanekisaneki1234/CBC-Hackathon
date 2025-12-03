"""
AI-powered meeting summarization using Claude
"""
import asyncio
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
from anthropic import Anthropic, AsyncAnthropic
from .config import Config

logger = logging.getLogger(__name__)


class MeetingSummarizer:
    """Generates AI-powered meeting summaries using Claude"""

    def __init__(self, on_summary: Optional[Callable] = None):
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        self.client = AsyncAnthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.on_summary = on_summary
        self.summaries: List[Dict[str, Any]] = []

    async def generate_summary(self, transcript: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a structured summary from transcript

        Args:
            transcript: The transcript text to summarize
            context: Optional context from previous summaries

        Returns:
            Dictionary containing the summary
        """
        if not transcript or len(transcript.strip()) < 50:
            logger.warning("Transcript too short for summary, skipping...")
            return {
                "timestamp": datetime.now().isoformat(),
                "summary": "Insufficient content for summary",
                "key_points": [],
                "decisions": [],
                "action_items": [],
                "questions": [],
            }

        try:
            logger.info("Generating summary with Claude...")

            # Build the prompt
            prompt = self._build_summary_prompt(transcript, context)

            # Call Claude API
            response = await self.client.messages.create(
                model=Config.CLAUDE_MODEL,
                max_tokens=1500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            summary_text = response.content[0].text

            # Create structured summary
            summary = {
                "timestamp": datetime.now().isoformat(),
                "summary": summary_text,
                "raw_transcript": transcript,
                "parsed": self._parse_summary(summary_text),
            }

            # Store summary
            self.summaries.append(summary)

            # Call callback if provided
            if self.on_summary:
                self.on_summary(summary)

            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "summary": f"Error generating summary: {str(e)}",
                "error": str(e),
            }

    def _build_summary_prompt(self, transcript: str, context: Optional[str] = None) -> str:
        """Build the prompt for Claude"""

        base_prompt = """Analyze the following meeting transcript segment and provide a structured summary.

Format your response as follows:

## Key Discussion Points
- [List main topics discussed with brief descriptions]

## Decisions Made
- [List any decisions or conclusions reached]

## Action Items
- [List action items with owners if mentioned, e.g., "John to review the proposal by Friday"]

## Important Questions/Concerns
- [List significant questions raised or concerns expressed]

## Overall Summary
[Provide a brief 2-3 sentence overview of this segment]

Keep the summary concise, factual, and well-organized. Focus on actionable information and key takeaways."""

        if context:
            prompt = f"""{base_prompt}

CONTEXT FROM PREVIOUS SUMMARIES:
{context}

CURRENT TRANSCRIPT SEGMENT:
{transcript}"""
        else:
            prompt = f"""{base_prompt}

TRANSCRIPT:
{transcript}"""

        return prompt

    def _parse_summary(self, summary_text: str) -> Dict[str, List[str]]:
        """
        Parse structured summary from Claude's response

        Returns:
            Dictionary with categorized content
        """
        parsed = {
            "key_points": [],
            "decisions": [],
            "action_items": [],
            "questions": [],
            "overview": "",
        }

        try:
            lines = summary_text.split("\n")
            current_section = None

            for line in lines:
                line = line.strip()

                if not line:
                    continue

                # Detect sections
                if "key discussion" in line.lower() or "discussion points" in line.lower():
                    current_section = "key_points"
                elif "decision" in line.lower():
                    current_section = "decisions"
                elif "action item" in line.lower():
                    current_section = "action_items"
                elif "question" in line.lower() or "concern" in line.lower():
                    current_section = "questions"
                elif "overall summary" in line.lower():
                    current_section = "overview"
                elif line.startswith("- ") or line.startswith("* "):
                    # Bullet point - add to current section
                    content = line[2:].strip()
                    if current_section and current_section != "overview":
                        parsed[current_section].append(content)
                elif current_section == "overview" and not line.startswith("#"):
                    # Add to overview
                    if parsed["overview"]:
                        parsed["overview"] += " " + line
                    else:
                        parsed["overview"] = line

        except Exception as e:
            logger.warning(f"Error parsing summary structure: {e}")

        return parsed

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Get all generated summaries"""
        return self.summaries

    def get_context_for_next_summary(self, num_previous: int = 2) -> str:
        """
        Get context from previous summaries

        Args:
            num_previous: Number of previous summaries to include

        Returns:
            Formatted context string
        """
        if not self.summaries:
            return ""

        recent = self.summaries[-num_previous:]
        context_parts = []

        for i, summary in enumerate(recent, 1):
            context_parts.append(f"Summary {i}:")
            if "parsed" in summary and summary["parsed"].get("overview"):
                context_parts.append(summary["parsed"]["overview"])
            else:
                # Fallback to first 200 chars of raw summary
                summary_text = summary.get("summary", "")
                context_parts.append(summary_text[:200] + "...")

        return "\n\n".join(context_parts)

    def export_summaries(self, format: str = "markdown") -> str:
        """
        Export all summaries in specified format

        Args:
            format: Output format ('markdown', 'json', or 'text')

        Returns:
            Formatted summary export
        """
        if format == "json":
            import json

            return json.dumps(self.summaries, indent=2)

        elif format == "markdown":
            output = "# Meeting Summaries\n\n"

            for i, summary in enumerate(self.summaries, 1):
                timestamp = summary.get("timestamp", "Unknown")
                output += f"## Summary {i} - {timestamp}\n\n"

                if "parsed" in summary:
                    parsed = summary["parsed"]

                    if parsed.get("overview"):
                        output += f"**Overview:** {parsed['overview']}\n\n"

                    if parsed.get("key_points"):
                        output += "**Key Points:**\n"
                        for point in parsed["key_points"]:
                            output += f"- {point}\n"
                        output += "\n"

                    if parsed.get("decisions"):
                        output += "**Decisions:**\n"
                        for decision in parsed["decisions"]:
                            output += f"- {decision}\n"
                        output += "\n"

                    if parsed.get("action_items"):
                        output += "**Action Items:**\n"
                        for item in parsed["action_items"]:
                            output += f"- {item}\n"
                        output += "\n"

                    if parsed.get("questions"):
                        output += "**Questions/Concerns:**\n"
                        for question in parsed["questions"]:
                            output += f"- {question}\n"
                        output += "\n"
                else:
                    output += summary.get("summary", "") + "\n\n"

                output += "---\n\n"

            return output

        else:  # text format
            output = "MEETING SUMMARIES\n" + "=" * 50 + "\n\n"

            for i, summary in enumerate(self.summaries, 1):
                timestamp = summary.get("timestamp", "Unknown")
                output += f"Summary {i} ({timestamp}):\n"
                output += "-" * 50 + "\n"
                output += summary.get("summary", "") + "\n\n"

            return output
