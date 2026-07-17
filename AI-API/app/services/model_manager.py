"""
Model Manager — Singleton quản lý load và cache tất cả AI models.
Load 1 lần duy nhất khi server khởi động, tái sử dụng cho mọi request.
"""

import time
import logging
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton quản lý tất cả AI models.

    Usage:
        manager = ModelManager()
        manager.load_models("/path/to/ai_models")
        result = manager.skin_gate.predict(image_bytes)
    """

    _instance: Optional["ModelManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.skin_gate = None
        self.segmentation = None
        self.classification = None
        self.device = None
        self._load_times = {}

    def load_models(self, model_dir: str, device: str = "auto"):
        """
        Load tất cả models từ thư mục ai_models.

        Args:
            model_dir: Đường dẫn tới thư mục ai_models/
            device: "auto", "cuda", hoặc "cpu"
        """
        model_dir = Path(model_dir)

        # Detect device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"🔧 Device: {self.device}")
        logger.info(f"📁 Model dir: {model_dir}")

        # ── Load Skin Validation (Skin Gate) ─────────────────────────
        self._load_skin_gate(model_dir / "skin_validation")

        # ── Load Segmentation ────────────────────────────────────────
        self._load_segmentation(model_dir / "segmentation")
        self._load_classification(model_dir / "classification")

        logger.info("✅ All models loaded successfully!")

    def _load_skin_gate(self, model_path: Path):
        """Load Skin Gate pipeline."""
        try:
            start = time.time()
            logger.info("📦 Loading Skin Validation model...")

            from ai_models.skin_validation.inference import SkinGatePipeline

            weight_file = model_path / "best_model_binary.pth"
            if not weight_file.exists():
                logger.error(f"❌ Skin Gate weights not found: {weight_file}")
                return

            self.skin_gate = SkinGatePipeline(
                model_path=str(weight_file),
                device=self.device,
            )

            elapsed = time.time() - start
            self._load_times["skin_validation"] = round(elapsed, 2)
            logger.info(f"✅ Skin Validation loaded in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"❌ Failed to load Skin Validation: {e}")
            self.skin_gate = None

    def _load_segmentation(self, model_path: Path):
        """Load Segmentation pipeline."""
        try:
            start = time.time()
            logger.info("📦 Loading Segmentation model...")

            from ai_models.segmentation.inference import SegmentationPipeline

            if not model_path.exists():
                logger.error(f"❌ Segmentation dir not found: {model_path}")
                return

            self.segmentation = SegmentationPipeline(
                model_dir=str(model_path),
                device=self.device,
            )

            elapsed = time.time() - start
            self._load_times["segmentation"] = round(elapsed, 2)
            logger.info(f"✅ Segmentation loaded in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"❌ Failed to load Segmentation: {e}")
            self.segmentation = None

    def _load_classification(self, model_path: Path):
        """Load the 10-class Custom EfficientNet-B0 v2 classifier."""
        try:
            start = time.time()
            logger.info("Loading Classification model...")

            from ai_models.classification.inference import ClassificationPipeline

            self.classification = ClassificationPipeline(
                model_dir=str(model_path),
                device=self.device,
            )
            elapsed = time.time() - start
            self._load_times["classification"] = round(elapsed, 2)
            logger.info(f"Classification loaded in {elapsed:.2f}s")
        except Exception as e:
            logger.error(f"Failed to load Classification: {e}", exc_info=True)
            self.classification = None

    def health_check(self) -> dict:
        """Trả về trạng thái của tất cả models."""
        return {
            "device": self.device,
            "models": {
                "skin_validation": {
                    "loaded": self.skin_gate is not None,
                    "architecture": "EfficientNet-B0",
                    "task": "Binary Classification (skin / not-skin)",
                    "load_time_s": self._load_times.get("skin_validation"),
                },
                "segmentation": {
                    "loaded": self.segmentation is not None,
                    "architecture": "U-Net + EfficientNet-B3",
                    "task": "Skin Lesion Segmentation",
                    "load_time_s": self._load_times.get("segmentation"),
                },
                "classification": {
                    "loaded": self.classification is not None,
                    "architecture": "Custom EfficientNet-B0 v2",
                    "task": "10-class Skin Disease Classification",
                    "load_time_s": self._load_times.get("classification"),
                },
            },
        }


# ── Singleton instance ───────────────────────────────────────────────
model_manager = ModelManager()
