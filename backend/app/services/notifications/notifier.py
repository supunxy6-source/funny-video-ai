"""
Stateside Smiles — Notification Service

Sends pipeline status notifications via Email (SMTP) and Slack webhooks.
"""

import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class Notifier:
    """Sends notifications via email and Slack."""

    async def notify_success(
        self,
        title: str,
        youtube_url: str,
        duration: float,
        processing_time: float,
        facebook_url: str = None,
    ) -> None:
        """Send success notification."""
        message = (
            f"✅ Video Published Successfully!\n\n"
            f"📺 Title: {title}\n"
            f"🔗 YouTube: {youtube_url}\n"
        )
        if facebook_url:
            message += f"📘 Facebook: {facebook_url}\n"
        message += (
            f"⏱️ Duration: {duration:.1f} minutes\n"
            f"🕐 Processing Time: {processing_time:.1f} minutes\n"
            f"📅 Published: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        )

        await self._send_email(
            subject=f"✅ Stateside Smiles: '{title}' published",
            body=message,
        )
        await self._send_slack(message)

    async def notify_failure(
        self,
        step_name: str,
        error_message: str,
        pipeline_run_id: str,
    ) -> None:
        """Send failure notification."""
        message = (
            f"❌ Pipeline Failed!\n\n"
            f"🔴 Step: {step_name}\n"
            f"🆔 Run ID: {pipeline_run_id}\n"
            f"❗ Error: {error_message}\n"
            f"📅 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Please check the admin dashboard for details."
        )

        await self._send_email(
            subject=f"❌ Stateside Smiles: Pipeline failed at {step_name}",
            body=message,
        )
        await self._send_slack(message)

    async def notify_daily_summary(
        self,
        videos_produced: int,
        articles_collected: int,
        total_duration: float,
    ) -> None:
        """Send daily summary notification."""
        message = (
            f"📊 Daily Summary — Stateside Smiles\n\n"
            f"📰 Articles collected: {articles_collected}\n"
            f"🎬 Videos produced: {videos_produced}\n"
            f"⏱️ Total content: {total_duration:.1f} minutes\n"
            f"📅 Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        )

        await self._send_email(
            subject="📊 Stateside Smiles: Daily Summary",
            body=message,
        )
        await self._send_slack(message)

    async def _send_email(self, subject: str, body: str) -> None:
        """Send email notification via SMTP."""
        if not settings.smtp_user or not settings.notification_email:
            logger.debug("Email notification skipped — SMTP not configured")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_from
            msg["To"] = settings.notification_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

            logger.info(f"📧 Email sent to {settings.notification_email}")

        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    async def _send_slack(self, message: str) -> None:
        """Send Slack notification via webhook."""
        if not settings.slack_webhook_url:
            logger.debug("Slack notification skipped — webhook not configured")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.slack_webhook_url,
                    json={"text": message},
                    timeout=10,
                )
                response.raise_for_status()
            logger.info("💬 Slack notification sent")
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")


# Singleton instance
notifier = Notifier()
