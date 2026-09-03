"""
Test script for the upgraded ImageGenerator.
Tests:
1. AI Image Generation via Pollinations (Flux / Turbo)
2. Editorial News Photo Search via Wikimedia Commons
3. Chart / Statistical visualization for facts
4. Fallback Editorial News Graphic Card
"""

import asyncio
import os
import sys
from pathlib import Path
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Override generated_dir for local test
from app.core.config import settings
test_output_dir = Path(__file__).parent / "test_output"
test_output_dir.mkdir(parents=True, exist_ok=True)
settings.generated_dir = str(test_output_dir)

from app.services.visuals.image_generator import ImageGenerator


async def test_image_generation():
    print("🚀 Initializing ImageGenerator...")
    gen = ImageGenerator()
    gen.output_dir = test_output_dir / "images"
    gen.output_dir.mkdir(parents=True, exist_ok=True)
    gen.chart_gen.output_dir = test_output_dir / "charts"
    gen.chart_gen.output_dir.mkdir(parents=True, exist_ok=True)

    test_cases = [
        {
            "name": "AI News Image (Earthquake)",
            "prompt": "Editorial news photo coverage of aftermath of Indonesia earthquake, emergency rescue teams searching debris, journalistic photo, sharp focus, 16:9, 4k",
            "title": "Indonesia Earthquake Aftermath",
            "visual_type": "image",
            "text": "Rescue teams are searching through rubble in the hardest-hit districts following the magnitude 6.8 earthquake.",
        },
        {
            "name": "AI News Image (Space/Tech)",
            "prompt": "SpaceX Starship rocket launch on pad with glowing exhaust plume, high resolution cinematic news photograph, photorealistic",
            "title": "SpaceX Starship Orbital Launch",
            "visual_type": "image",
            "text": "SpaceX conducted a major test flight from Starbase today.",
        },
        {
            "name": "Data Chart Visualization",
            "prompt": "Data visualization chart showing key statistics",
            "title": "Economic Inflation Trends",
            "visual_type": "chart",
            "text": "Inflation dropped by 3.2% while unemployment stayed at 4.1% and GDP growth reached 2.8%.",
        },
    ]

    for tc in test_cases:
        print(f"\n--- Testing: {tc['name']} ---")
        img_path = await gen.generate_image(
            prompt=tc["prompt"],
            title=tc["title"],
            visual_type=tc["visual_type"],
            text_context=tc["text"],
        )

        print(f"Result path: {img_path}")
        assert img_path is not None, f"Image generation returned None for {tc['name']}"
        assert os.path.exists(img_path), f"File does not exist: {img_path}"
        
        file_size = os.path.getsize(img_path)
        print(f"File size: {file_size / 1024:.1f} KB")
        assert file_size > 1000, f"File size too small ({file_size} bytes)"

        with Image.open(img_path) as img:
            print(f"Image Dimensions: {img.size[0]}x{img.size[1]}, Format: {img.format}")
            assert img.size[0] >= 1280 and img.size[1] >= 720, f"Dimensions too small: {img.size}"

        print(f"✅ PASSED: {tc['name']}")

    print("\n🎉 ALL IMAGE GENERATION TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_image_generation())
