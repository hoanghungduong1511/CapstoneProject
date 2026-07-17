from __future__ import annotations

from app.config import settings
from app.data.disease_catalog import extract_disease_labels_from_text, get_disease_metadata
from app.schemas.chat import (
    ChatGenerateRequest,
    ChatGenerateResponse,
    MedicalChatRequest,
    MedicalChatResponse,
)
from app.services.llm_service import llm_service
from app.services.medical_context_service import (
    build_medical_context,
    select_missing_questions,
)
from app.services.prompt_builder import build_chat_prompt
from app.services.rag_service import rag_service
from app.services.safety_service import (
    classify_medical_safety,
    infer_symptom_updates,
)


DISCLAIMER = "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."


class ChatbotService:
    async def generate(self, request: ChatGenerateRequest) -> ChatGenerateResponse:
        context = dict(request.medical_context)
        topk_labels = [
            item.get("label", "")
            for item in context.get("classification_topk") or []
        ]
        explicit_labels = extract_disease_labels_from_text(request.user_question)
        if explicit_labels:
            topk_labels = explicit_labels

        conversation_text = " ".join(
            [
                item.content
                for item in request.chat_history
                if item.role == "user"
            ]
            + [request.user_question]
        )
        symptom_updates = infer_symptom_updates(conversation_text)
        if symptom_updates:
            symptoms = dict(context.get("user_symptoms") or {})
            symptoms.update(symptom_updates)
            context["user_symptoms"] = symptoms
            context["missing_questions"] = select_missing_questions(
                symptoms,
                topk_labels,
            )

        missing_questions = list(context.get("missing_questions") or [])
        safety_level = classify_medical_safety(request.user_question, context)

        if context.get("image_valid", True):
            retrieval = rag_service.retrieve(request.user_question, topk_labels)
        else:
            retrieval = rag_service.retrieve("", [])

        instructions, messages = build_chat_prompt(
            request.user_question,
            context,
            retrieval.final_context,
            [item.model_dump() for item in request.chat_history],
        )
        result = await llm_service.generate(
            instructions,
            messages,
            context,
            retrieval.chunks,
            missing_questions,
            safety_level,
            request.user_question,
        )

        return ChatGenerateResponse(
            answer=result["answer"],
            safety_level=safety_level,
            sources=retrieval.sources,
            missing_questions=missing_questions,
            retrieved_chunks=retrieval.chunks,
            rewritten_query=retrieval.rewritten_query,
            model_name=result["model_name"],
            token_usage=result["token_usage"],
        )

    async def reply(self, request: MedicalChatRequest) -> MedicalChatResponse:
        analysis = request.analysis.model_dump() if request.analysis else {}
        symptoms = request.patient.model_dump() if request.patient else {}
        context = build_medical_context(analysis, symptoms)
        generated = await self.generate(
            ChatGenerateRequest(
                user_question=request.message,
                medical_context=context,
                chat_history=request.history,
            )
        )
        top_label = (
            context["classification_topk"][0]["label"]
            if context["classification_topk"]
            else None
        )
        disease = get_disease_metadata(top_label)
        confidence = (
            context["classification_topk"][0].get("confidence")
            if context["classification_topk"]
            else None
        )
        confidence_note = None
        if confidence is not None:
            value = confidence * 100 if confidence <= 1 else confidence
            confidence_note = (
                f"Độ phù hợp top-1 là {value:.1f}%; đây không phải mức độ nặng."
            )

        return MedicalChatResponse(
            message=generated.answer,
            source=(
                "mock"
                if generated.model_name == "mock-medical-rag-v2"
                else (
                    "gemini"
                    if generated.model_name == settings.GEMINI_MODEL
                    or generated.model_name.casefold().startswith("gemini")
                    else "openai"
                )
            ),
            model=generated.model_name,
            normalized_label=top_label,
            disease_name=disease["name_vi"] if disease else None,
            urgency=generated.safety_level,
            confidence_note=confidence_note,
            disclaimer=DISCLAIMER,
            safety_level=generated.safety_level,
            sources=generated.sources,
            missing_questions=generated.missing_questions,
        )


chatbot_service = ChatbotService()
