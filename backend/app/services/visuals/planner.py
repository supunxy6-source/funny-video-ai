"""
Stateside Smiles — Visual Planner

Analyzes script scenes and plans visual assets: AI-generated images,
charts, maps, animations, and stock footage suggestions.
"""

import json
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.scene import Scene
from app.models.script import Script

logger = logging.getLogger(__name__)


class VisualPlanner:
    """Plans visual assets for each scene in a video script."""

    def plan_visuals(self, scenes: list[dict]) -> list[dict]:
        """
        Generate a visual storyboard for the script.
        Decides what type of visual each scene needs and creates prompts.
        """
        storyboard = []

        for scene in scenes:
            visual_plan = {
                "scene_id": scene.get("id"),
                "order": scene.get("order", 0),
                "scene_type": scene.get("scene_type", "narration"),
                "visual_type": "video",
                "visual_prompt": scene.get("visual_prompt", ""),
                "needs_generation": True,
            }

            # Enhance visual prompts based on scene type
            scene_type = scene.get("scene_type", "")
            if scene_type == "hook":
                visual_plan["visual_prompt"] = self._enhance_hook_prompt(
                    scene.get("visual_prompt", ""), scene.get("text", "")
                )
            elif scene_type == "facts":
                visual_plan["visual_type"] = "video"
                visual_plan["visual_prompt"] = self._enhance_editorial_prompt(
                    scene.get("visual_prompt", ""), scene.get("text", "")
                )
            elif scene_type == "impact":
                visual_plan["visual_type"] = "video"
                visual_plan["visual_prompt"] = self._enhance_impact_prompt(
                    scene.get("visual_prompt", ""), scene.get("text", "")
                )
            elif scene_type == "cta":
                visual_plan["visual_type"] = "animation"
                visual_plan["needs_generation"] = False  # Use pre-made outro
            elif scene_type in ["intro", "timeline", "context", "conclusion"]:
                visual_plan["visual_prompt"] = self._enhance_editorial_prompt(
                    scene.get("visual_prompt", ""), scene.get("text", "")
                )

            storyboard.append(visual_plan)

        logger.info(f"🎬 Visual storyboard planned: {len(storyboard)} scenes")
        return storyboard

    def _enhance_hook_prompt(self, base_prompt: str, text: str) -> str:
        """Create a dramatic, motion-oriented video prompt for the hook scene."""
        snippet = text[:150].strip() if text else ""
        context = f" Context: {snippet}." if snippet else ""
        return (
            f"{base_prompt}.{context} "
            "Cinematic tracking shot pushing in rapidly towards the subject, "
            "dramatic camera movement with shallow depth of field, "
            "dynamic lighting shifts and atmospheric haze, "
            "people and objects in motion, urgent fast-paced broadcast news footage, "
            "vertical 9:16 composition, professional video quality"
        )

    def _enhance_editorial_prompt(self, base_prompt: str, text: str) -> str:
        """Enhance a standard scene prompt with cinematic motion descriptions for video generation."""
        snippet = text[:150].strip() if text else ""
        context = f" Context: {snippet}." if snippet else ""
        return (
            f"{base_prompt}.{context} "
            "Smooth dolly shot with steady camera movement through the scene, "
            "environmental motion — wind, traffic, people walking, flags waving, "
            "authentic documentary-style footage with natural camera sway, "
            "broadcast news B-roll quality, continuous realistic motion, "
            "vertical 9:16 composition, 4K cinematic video"
        )

    def _enhance_impact_prompt(self, base_prompt: str, text: str) -> str:
        """Create a dramatic pull-back reveal prompt for impact/significance scenes."""
        snippet = text[:150].strip() if text else ""
        context = f" Context: {snippet}." if snippet else ""
        return (
            f"{base_prompt}.{context} "
            "Dramatic slow-motion crane shot pulling back to reveal the full scope, "
            "sweeping aerial perspective with parallax depth, "
            "atmospheric volumetric lighting and motion blur, "
            "cinematic news documentary reveal shot, "
            "vertical 9:16 composition, broadcast quality video"
        )


async def plan_visuals_for_script(script_id: int) -> list[dict]:
    """
    Main visual planning entry point called by Celery task.
    Reads script scenes from DB, plans visuals, and updates scene records.
    """
    planner = VisualPlanner()

    async with async_session_factory() as db:
        result = await db.execute(
            select(Scene)
            .where(Scene.script_id == script_id)
            .order_by(Scene.order)
        )
        scenes = result.scalars().all()

        if not scenes:
            logger.warning(f"No scenes found for script {script_id}")
            return []

        scene_dicts = [
            {
                "id": s.id,
                "order": s.order,
                "scene_type": s.scene_type,
                "title": s.title,
                "text": s.text,
                "visual_prompt": s.visual_prompt,
                "visual_type": s.visual_type,
            }
            for s in scenes
        ]

        storyboard = planner.plan_visuals(scene_dicts)

        # Update scene records with enhanced visual prompts
        for plan in storyboard:
            scene_id = plan.get("scene_id")
            if scene_id:
                scene = await db.get(Scene, scene_id)
                if scene:
                    scene.visual_prompt = plan["visual_prompt"]
                    scene.visual_type = plan["visual_type"]

        await db.commit()
        logger.info(f"💾 Visual plans saved for script {script_id}")

        return storyboard
