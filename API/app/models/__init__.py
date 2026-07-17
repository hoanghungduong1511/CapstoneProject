# Models package
# Import tất cả models để Alembic và SQLAlchemy nhận diện

from app.models.user import User  # noqa: F401
from app.models.image import Image  # noqa: F401
from app.models.ai_result import AIResult  # noqa: F401
from app.models.classification_result import ClassificationResult  # noqa: F401
from app.models.segmentation_result import SegmentationResult  # noqa: F401
from app.models.medical_context import MedicalContext  # noqa: F401
from app.models.input_validation import InputValidation  # noqa: F401
from app.models.ai_feature import AIFeature  # noqa: F401
from app.models.chat_session import ChatSession  # noqa: F401
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.rag_query import RAGQuery  # noqa: F401
from app.models.rag_result import RAGResult  # noqa: F401
from app.models.disease_knowledge import DiseaseKnowledge  # noqa: F401
