"""NLP classifier using Gemini 1.5 Flash (zero-shot).

Classifies scraped posts as problem / non-problem and extracts:
    - is_problem    : bool
    - confidence    : float 0-1
    - category      : Technology | Health | Finance | Relationships |
                      Productivity | Travel | Education | Career | Other
    - sentiment     : urgent | frustrated | curious | neutral
    - summary       : 2-sentence problem summary

Posts with body shorter than 20 characters are skipped (cost control).
Confidence threshold < 0.65 sets review_required flag on the DB row.

Retry policy: exponential backoff, max 3 attempts per API call.
Batch processing: groups of 10 posts with a 1-second inter-batch delay.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = structlog.get_logger(__name__)

CLASSIFICATION_PROMPT_TEMPLATE = """\
Analyze this social media post and respond ONLY with valid JSON.

Post title: {title}
Post body: {body}

Instructions:
1. Is this post describing a real problem or pain point? (YES/NO)
2. If YES, assign one category from: Technology, Health, Finance, \
Relationships, Productivity, Travel, Education, Career, Other
3. What is the emotional sentiment? Choose one: urgent, frustrated, \
curious, neutral
4. Write a 2-sentence summary of the problem (leave empty string if \
not a problem).

Respond with this exact JSON structure (no markdown, no extra keys):
{{
  "is_problem": <true|false>,
  "confidence": <float between 0.0 and 1.0>,
  "category": "<category string or empty string>",
  "sentiment": "<urgent|frustrated|curious|neutral>",
  "summary": "<2-sentence summary or empty string>"
}}
"""

REVIEW_CONFIDENCE_THRESHOLD = 0.65
MIN_BODY_LENGTH = 20
BATCH_SIZE = 10
INTER_BATCH_SLEEP = 1.0  # seconds


@dataclass
class ClassificationResult:
    """Structured output from the NLP classifier."""

    is_problem: bool
    confidence: float
    category: str
    sentiment: str
    summary: str
    review_required: bool = False

    def __post_init__(self) -> None:
        # Clamp confidence to [0.0, 1.0]
        self.confidence = max(0.0, min(1.0, float(self.confidence)))
        # Auto-flag low-confidence classifications
        if self.confidence < REVIEW_CONFIDENCE_THRESHOLD:
            self.review_required = True


class NLPClassifier:
    """Zero-shot classifier powered by Gemini 1.5 Flash."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-1.5-flash")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def classify(self, title: str, body: str) -> ClassificationResult | None:
        """Classify a single post.

        Parameters
        ----------
        title : str — post title
        body  : str — post body / self-text

        Returns
        -------
        ClassificationResult or None if classification was skipped or failed.
        """
        body = body or ""
        if len(body.strip()) < MIN_BODY_LENGTH:
            logger.debug(
                "Skipping classification: body too short",
                title=title[:60],
                body_len=len(body),
            )
            return None

        return self._call_gemini(title, body)

    def classify_batch(
        self,
        posts: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], ClassificationResult | None]]:
        """Classify a list of posts in batches of BATCH_SIZE.

        Parameters
        ----------
        posts : list of dicts with at least 'title' and 'body' keys

        Returns
        -------
        list of (post_dict, ClassificationResult | None) tuples
        """
        results: list[tuple[dict[str, Any], ClassificationResult | None]] = []

        for batch_start in range(0, len(posts), BATCH_SIZE):
            batch = posts[batch_start : batch_start + BATCH_SIZE]
            for post in batch:
                result = self.classify(
                    title=post.get("title") or "",
                    body=post.get("body") or "",
                )
                results.append((post, result))

            # Rate-control between batches (not needed for the last batch)
            if batch_start + BATCH_SIZE < len(posts):
                time.sleep(INTER_BATCH_SLEEP)

        logger.info(
            "Batch classification complete",
            total=len(posts),
            classified=sum(1 for _, r in results if r is not None),
        )
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=False,
    )
    def _call_gemini(self, title: str, body: str) -> ClassificationResult | None:
        """Call Gemini API with retry/backoff.

        Returns None if all retries are exhausted or the response cannot
        be parsed as valid JSON.
        """
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            title=title[:500],
            body=body[:2000],
        )

        try:
            response = self._model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=512,
                ),
            )
            raw_text = response.text.strip()
            return self._parse_response(raw_text)

        except Exception as exc:
            logger.warning(
                "Gemini API error during classification",
                error=str(exc),
                title=title[:60],
            )
            raise  # tenacity will handle retries

    @staticmethod
    def _parse_response(raw: str) -> ClassificationResult | None:
        """Parse the Gemini JSON response into a ClassificationResult.

        Strips accidental markdown code fences if present.
        Returns None if the JSON is malformed.
        """
        # Strip markdown code blocks Gemini occasionally wraps output in
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Remove first and last fence lines
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse Gemini JSON", error=str(exc), raw=raw[:200])
            return None

        try:
            return ClassificationResult(
                is_problem=bool(data.get("is_problem", False)),
                confidence=float(data.get("confidence", 0.0)),
                category=str(data.get("category") or "").strip(),
                sentiment=str(data.get("sentiment") or "neutral").strip().lower(),
                summary=str(data.get("summary") or "").strip(),
            )
        except (TypeError, ValueError) as exc:
            logger.warning(
                "Invalid classification data structure",
                error=str(exc),
                data=data,
            )
            return None
