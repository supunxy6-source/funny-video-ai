"""
AI News Studio — Chart Generator

Generates data visualizations (charts, graphs) for statistics
mentioned in news scripts using matplotlib.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates data visualization images for video scenes."""

    def __init__(self):
        self.output_dir = Path(settings.generated_dir) / "charts"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set dark theme for charts
        plt.style.use("dark_background")
        self.colors = ["#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8", "#4DD0E1"]

    def generate_bar_chart(
        self,
        title: str,
        labels: list[str],
        values: list[float],
        ylabel: str = "",
    ) -> Optional[str]:
        """Generate a bar chart image."""
        try:
            fig, ax = plt.subplots(figsize=(9, 16), dpi=150)
            fig.patch.set_facecolor("#1a1a2e")
            ax.set_facecolor("#1a1a2e")

            bars = ax.bar(
                labels, values,
                color=self.colors[:len(labels)],
                edgecolor="white",
                linewidth=0.5,
                width=0.6,
            )

            ax.set_title(title, fontsize=24, fontweight="bold", color="white", pad=20)
            ax.set_ylabel(ylabel, fontsize=14, color="white")
            ax.tick_params(axis="both", colors="white", labelsize=12)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color("#444")
            ax.spines["left"].set_color("#444")
            ax.grid(axis="y", alpha=0.2, color="white")

            # Add value labels on bars
            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{val:,.0f}", ha="center", va="bottom",
                    fontsize=14, fontweight="bold", color="white",
                )

            plt.tight_layout()
            file_path = self.output_dir / f"chart_{uuid.uuid4().hex}.png"
            plt.savefig(file_path, bbox_inches="tight", facecolor="#1a1a2e")
            plt.close(fig)

            logger.info(f"📊 Chart generated: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            plt.close("all")
            return None

    def generate_line_chart(
        self,
        title: str,
        x_labels: list[str],
        y_values: list[float],
        ylabel: str = "",
    ) -> Optional[str]:
        """Generate a line chart image."""
        try:
            fig, ax = plt.subplots(figsize=(9, 16), dpi=150)
            fig.patch.set_facecolor("#1a1a2e")
            ax.set_facecolor("#1a1a2e")

            ax.plot(
                x_labels, y_values,
                color="#4FC3F7", linewidth=3,
                marker="o", markersize=8,
                markerfacecolor="#81C784", markeredgecolor="white",
            )
            ax.fill_between(
                range(len(x_labels)), y_values,
                alpha=0.15, color="#4FC3F7",
            )

            ax.set_title(title, fontsize=24, fontweight="bold", color="white", pad=20)
            ax.set_ylabel(ylabel, fontsize=14, color="white")
            ax.tick_params(axis="both", colors="white", labelsize=12)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["bottom"].set_color("#444")
            ax.spines["left"].set_color("#444")
            ax.grid(alpha=0.2, color="white")

            plt.tight_layout()
            file_path = self.output_dir / f"chart_{uuid.uuid4().hex}.png"
            plt.savefig(file_path, bbox_inches="tight", facecolor="#1a1a2e")
            plt.close(fig)

            logger.info(f"📈 Line chart generated: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Line chart generation failed: {e}")
            plt.close("all")
            return None

    def generate_stat_card(
        self,
        title: str,
        value: str,
        subtitle: str = "",
    ) -> Optional[str]:
        """Generate a full-screen statistic card image."""
        try:
            fig, ax = plt.subplots(figsize=(9, 16), dpi=150)
            fig.patch.set_facecolor("#1a1a2e")
            ax.set_facecolor("#1a1a2e")
            ax.axis("off")

            ax.text(
                0.5, 0.65, value,
                transform=ax.transAxes, fontsize=72, fontweight="bold",
                color="#4FC3F7", ha="center", va="center",
            )
            ax.text(
                0.5, 0.40, title,
                transform=ax.transAxes, fontsize=28, fontweight="bold",
                color="white", ha="center", va="center",
            )
            if subtitle:
                ax.text(
                    0.5, 0.28, subtitle,
                    transform=ax.transAxes, fontsize=18,
                    color="#888", ha="center", va="center",
                )

            file_path = self.output_dir / f"stat_{uuid.uuid4().hex}.png"
            plt.savefig(file_path, bbox_inches="tight", facecolor="#1a1a2e")
            plt.close(fig)

            logger.info(f"📊 Stat card generated: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Stat card generation failed: {e}")
            plt.close("all")
            return None
