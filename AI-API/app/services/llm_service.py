from __future__ import annotations

import asyncio

import json

import urllib.error

import urllib.request

import logging

import re

import unicodedata

from typing import Any

from app.config import settings

from app.services.safety_service import enforce_answer_guardrails

logger = logging.getLogger(__name__)

class LLMService:

    def __init__(self) -> None:

        self._client = None

    def _get_client(self):

        if self._client is not None:

            return self._client

        if not settings.OPENAI_API_KEY:

            return None

        try:

            from openai import OpenAI

        except ImportError:

            logger.warning("openai package is unavailable; using fallback LLM")

            return None

        self._client = OpenAI(

            api_key=settings.OPENAI_API_KEY,

            timeout=settings.OPENAI_TIMEOUT_SECONDS,

            max_retries=2,

        )

        return self._client

    def _call_openai(

        self,

        instructions: str,

        messages: list[dict[str, str]],

    ) -> dict[str, Any]:

        client = self._get_client()

        if client is None:

            raise RuntimeError("OPENAI_API_KEY is not configured")

        # Use standard Chat Completions API instead of the experimental responses API

        # Map instructions to system message

        sys_msg = [{"role": "system", "content": instructions}] if instructions else []

        chat_messages = sys_msg + messages

        

        response = client.chat.completions.create(

            model=settings.OPENAI_MODEL,

            messages=chat_messages,

            temperature=settings.CHATBOT_TEMPERATURE,

            max_tokens=settings.CHATBOT_MAX_TOKENS,

        )

        

        # Extract text from standard completion response

        output_text = ""

        if response.choices and len(response.choices) > 0:

            output_text = response.choices[0].message.content or ""

        usage = getattr(response, "usage", None)

        token_usage = None

        if usage:

            token_usage = {

                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),

                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),

                "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),

            }

        return {

            "answer": enforce_answer_guardrails(output_text),

            "model_name": settings.OPENAI_MODEL,

            "token_usage": token_usage,

            "source": "openai",

        }


    def _call_gemini(

        self,

        instructions: str,

        messages: list[dict[str, str]],

    ) -> dict[str, Any]:

        if not settings.GEMINI_API_KEY:

            raise RuntimeError("GEMINI_API_KEY is not configured")

        url = (

            "https://generativelanguage.googleapis.com/v1beta/models/"

            f"{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

        )

        contents: list[dict[str, Any]] = []

        for message in messages:

            role = "model" if message.get("role") == "assistant" else "user"

            content = str(message.get("content") or "").strip()

            if not content:

                continue

            contents.append({"role": role, "parts": [{"text": content}]})

        payload: dict[str, Any] = {

            "contents": contents,

            "generationConfig": {

                "temperature": settings.CHATBOT_TEMPERATURE,

                "maxOutputTokens": settings.CHATBOT_MAX_TOKENS,

            },

        }

        if instructions:

            payload["systemInstruction"] = {"parts": [{"text": instructions}]}

        request = urllib.request.Request(

            url,

            data=json.dumps(payload).encode("utf-8"),

            headers={"Content-Type": "application/json"},

            method="POST",

        )

        try:

            with urllib.request.urlopen(

                request,

                timeout=settings.GEMINI_TIMEOUT_SECONDS,

            ) as response:

                data = json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:

            detail = exc.read().decode("utf-8", errors="replace")

            raise RuntimeError(f"Gemini request failed: {exc.code} {detail}") from exc

        output_parts: list[str] = []
        finish_reasons: list[str] = []

        for candidate in data.get("candidates") or []:
            finish_reason = str(candidate.get("finishReason") or "").strip()
            if finish_reason:
                finish_reasons.append(finish_reason)

            content = candidate.get("content") or {}

            for part in content.get("parts") or []:

                text = part.get("text")

                if text:

                    output_parts.append(str(text))

            if output_parts:

                break

        if not output_parts:
            raise RuntimeError(
                "Gemini returned no answer text"
                + (f" (finish_reasons={finish_reasons})" if finish_reasons else "")
            )

        usage = data.get("usageMetadata") or {}

        token_usage = None

        if usage:

            token_usage = {

                "input_tokens": int(usage.get("promptTokenCount") or 0),

                "output_tokens": int(usage.get("candidatesTokenCount") or 0),

                "total_tokens": int(usage.get("totalTokenCount") or 0),

            }

        answer = enforce_answer_guardrails("\n".join(output_parts).strip())
        if any(
            reason in {"MAX_TOKENS", "SAFETY", "RECITATION", "OTHER"}
            for reason in finish_reasons
        ):
            raise RuntimeError(
                f"Gemini returned unfinished or blocked answer: {finish_reasons}"
            )

        return {

            "answer": answer,

            "model_name": settings.GEMINI_MODEL,

            "token_usage": token_usage,

            "source": "gemini",

            "finish_reasons": finish_reasons,

        }

    @staticmethod
    def _looks_incomplete_answer(result: dict[str, Any]) -> bool:
        answer = str(result.get("answer") or "").strip()
        if not answer:
            return True

        token_usage = result.get("token_usage") or {}
        output_tokens = token_usage.get("output_tokens")
        try:
            output_token_count = int(output_tokens) if output_tokens is not None else None
        except (TypeError, ValueError):
            output_token_count = None

        has_disclaimer = "Thông tin chỉ mang tính tham khảo" in answer
        if output_token_count is not None and output_token_count < 80 and not has_disclaimer:
            return True

        last_char = answer[-1]
        if last_char not in ".!?:" and len(answer) < 500 and not has_disclaimer:
            return True

        if re.search(r"(?m)^\s*#{1,6}\s*(?:\d+[.)]?\s*)?.{0,14}$", answer):
            return True

        trailing_fragments = (
            "do phu",
            "huong",
            "dau",
            "trieu",
            "cham soc co",
            "bat",
        )
        normalized = LLMService._normalize_text(answer)
        return any(normalized.endswith(fragment) for fragment in trailing_fragments)

    @staticmethod

    def _normalize_text(value: str) -> str:

        decomposed = unicodedata.normalize("NFD", value.casefold())

        without_accents = "".join(

            char for char in decomposed

            if unicodedata.category(char) != "Mn"

        )

        without_accents = without_accents.replace("đ", "d").replace("Đ", "d")

        without_accents = without_accents.replace("\u0111", "d").replace("\u0110", "d")

        without_accents = re.sub(r"[^a-z0-9]+", " ", without_accents)

        return re.sub(r"\s+", " ", without_accents).strip()

    @staticmethod

    def _strip_section_prefix(text: str) -> str:

        """Strip known section prefixes like 'Mục: ...' from chunk text."""

        stripped = text.strip()

        for prefix in ("Mục:", "Chủ đề:", "Tiêu đề:"):

            if stripped.startswith(prefix):

                return stripped[len(prefix):].strip()

        return stripped

    @staticmethod

    def _capitalize_first(text: str) -> str:

        stripped = text.strip()

        if not stripped:

            return ""

        return stripped[0].upper() + stripped[1:]

    @classmethod

    def _format_section(

        cls,

        title: str,

        content: str,

        bulletize: bool = True,

    ) -> str:

        content = content.strip()

        if not content:

            return ""

        normalized_content = cls._normalize_text(content)

        normalized_title = cls._normalize_text(title)

        if normalized_content.startswith(normalized_title.rstrip()):

            return cls._capitalize_first(content)

        if not bulletize:

            return f"{title}\n{cls._capitalize_first(content)}"

        items = [

            cls._capitalize_first(item)

            for item in re.split(r"\s*;\s*", content)

            if item.strip()

        ]

        if len(items) <= 1:

            return f"{title}\n- {cls._capitalize_first(content)}"

        return f"{title}\n" + "\n".join(f"- {item}" for item in items)

    @staticmethod

    def _chunk_line(chunk: dict[str, Any] | None, index: int) -> str:

        if not chunk:

            return ""

        lines = [

            line.strip()

            for line in str(chunk.get("content", "")).splitlines()

            if line.strip()

        ]

        for line in lines:

            if line.casefold().startswith("nội dung:"):

                return line.split(":", 1)[1].strip()

        return lines[index] if len(lines) > index else ""

    @classmethod

    def _chunk_body(cls, chunk: dict[str, Any] | None) -> str:

        if not chunk:

            return ""

        lines = [

            line.strip()

            for line in str(chunk.get("content", "")).splitlines()

            if line.strip()

        ]

        # First priority: find "Nội dung:" line and return its content

        for line in lines:

            normalized = cls._normalize_text(line)

            if normalized.startswith("noi dung") or line.casefold().startswith("nội dung:"):

                return line.split(":", 1)[1].strip()

        # Fallback: skip header lines ("Bệnh:", "Mục:") and return first content line

        for line in lines:

            normalized_lower = line.casefold()

            if any(normalized_lower.startswith(p) for p in ("bệnh:", "mục:", "chủ đề:")):

                continue

            return cls._strip_section_prefix(line)

        return lines[0] if lines else ""

    @classmethod

    def _first_chunk_body_by_type(

        cls,

        chunks: list[dict[str, Any]],

        chunk_type: str,

    ) -> str:

        for item in chunks:

            if item.get("chunk_type") == chunk_type:

                return cls._chunk_content(item)

        return ""

    @classmethod

    def _chunk_by_type(

        cls,

        chunks: list[dict[str, Any]],

        chunk_type: str,

    ) -> dict[str, Any] | None:

        for item in chunks:

            if item.get("chunk_type") == chunk_type:

                return item

        return None

    @classmethod

    def _chunk_content(cls, chunk: dict[str, Any] | None) -> str:

        if not chunk:

            return ""

        lines = [

            line.strip()

            for line in str(chunk.get("content", "")).splitlines()

            if line.strip()

        ]

        # Find "Nội dung:" line using accent-stripped matching

        for line in lines:

            normalized = cls._normalize_text(line)

            if normalized.startswith("noi dung") or line.casefold().startswith("nội dung:"):

                return line.split(":", 1)[1].strip()

        return cls._chunk_body(chunk)

    @staticmethod

    def _abcde_note(chunks: list[dict[str, Any]]) -> str:

        labels = {str(item.get("label") or "").upper() for item in chunks}

        content = "\n".join(str(item.get("content") or "") for item in chunks)

        if labels & {"NEVUS", "MELANOMA"} or "ABCDE" in content.upper():

            return (

                "ABCDE là quy tắc theo dõi nốt sắc tố: A là bất đối xứng, "

                "B là bờ không đều, C là màu không đồng nhất, D là kích thước lớn hoặc tăng, "

                "E là tiến triển/thay đổi theo thời gian."

            )

        return ""

    @staticmethod

    def _normalize_source_url(url: str) -> str:

        return url.strip().rstrip("/").casefold()

    @classmethod

    def _sources_text(

        cls,

        chunks: list[dict[str, Any]],

        max_sources: int = 3,

    ) -> str:

        primary_label = next(

            (

                str(item.get("label") or "").upper()

                for item in chunks

                if item.get("label")

            ),

            "",

        )

        source_chunks = [

            item

            for item in chunks

            if item.get("chunk_type") == "sources"

            and (

                not primary_label

                or str(item.get("label") or "").upper() == primary_label

            )

        ]

        same_label_chunks = [

            item

            for item in chunks

            if item not in source_chunks

            and (

                not primary_label

                or str(item.get("label") or "").upper() == primary_label

            )

        ]

        seen: set[str] = set()

        sources: list[str] = []

        for item in [*source_chunks, *same_label_chunks]:

            for raw_source in item.get("sources") or []:

                for source in str(raw_source).split("|"):

                    source = source.strip()

                    if not source:

                        continue

                    key = cls._normalize_source_url(source)

                    if key in seen:

                        continue

                    seen.add(key)

                    sources.append(source)

                    if len(sources) >= max_sources:

                        return "Nguồn tham khảo:\n" + "\n".join(

                            f"- {source}" for source in sources

                        )

        if sources:

            return "Nguồn tham khảo:\n" + "\n".join(f"- {source}" for source in sources)

        other_chunks = [

            item

            for item in chunks

            if item not in source_chunks and item not in same_label_chunks

        ]

        for item in other_chunks:

            for raw_source in item.get("sources") or []:

                for source in str(raw_source).split("|"):

                    source = source.strip()

                    if not source:

                        continue

                    key = cls._normalize_source_url(source)

                    if key in seen:

                        continue

                    seen.add(key)

                    sources.append(source)

                    if len(sources) >= max_sources:

                        return "Nguồn tham khảo:\n" + "\n".join(

                            f"- {source}" for source in sources

                        )

        if not sources:

            return "Tôi chưa tìm thấy nguồn tham khảo phù hợp trong context hiện tại."

        return "Nguồn tham khảo:\n" + "\n".join(f"- {source}" for source in sources)

    @classmethod

    def _mock_answer(

        cls,

        medical_context: dict[str, Any],

        chunks: list[dict[str, Any]],

        missing_questions: list[str],

        safety_level: str,

        user_question: str = "",

    ) -> str:

        if not medical_context.get("image_valid", True):

            return (

                "Ảnh hiện tại chưa đủ điều kiện để phân tích bệnh da. Vui lòng tải "

                "ảnh khác rõ nét, đủ sáng và tập trung vào vùng da cần kiểm tra."

            )

        normalized_question = cls._normalize_text(user_question)

        symptoms = medical_context.get("user_symptoms") or {}

        chunk = chunks[0] if chunks else None

        disease_name = (

            str(chunk.get("name_vi"))

            if chunk

            else "tình trạng da đang được phân tích"

        )

        if normalized_question in {

            "hi",

            "hello",

            "chao",

            "chao ban",

            "xin chao",

        }:

            if symptoms.get("bleed") or symptoms.get("ulcerated"):

                return (

                    "Chào bạn. Tôi đã ghi nhận vùng tổn thương có chảy máu hoặc "

                    "loét. Dù kích thước chưa thay đổi, bạn nên tránh cào, nặn hoặc "

                    "tự bôi thuốc mạnh và sắp xếp khám bác sĩ da liễu sớm.\n\n"

                    "Nếu máu chảy nhiều, không cầm, kèm đau tăng hoặc dấu hiệu "

                    "nhiễm trùng, hãy đi khám khẩn cấp."

                )

            return (

                f"Chào bạn. Tôi có thể hỗ trợ giải thích kết quả gợi ý liên quan "

                f"đến {disease_name}, hướng dẫn chăm sóc cơ bản và nhận biết dấu "

                "hiệu cần đi khám. Bạn muốn tìm hiểu nội dung nào?"

            )

        if any(

            phrase in normalized_question

            for phrase in (

                "ban la ai",

                "ban la gi",

                "ai day",

                "tro ly la ai",

                "tro ly gi",

                "who are you",

            )

        ):

            return (

                "Tôi là Trợ lý Y khoa AI của SkinAI. Tôi hỗ trợ giải thích kết quả "

                "phân tích ảnh da, cung cấp thông tin tham khảo về bệnh da liễu, "

                "gợi ý cách chăm sóc an toàn và thời điểm nên đi khám.\n\n"

                "Tôi không thay thế bác sĩ và không đưa ra chẩn đoán xác định."

            )

        if any(

            phrase in normalized_question

            for phrase in (

                "bo qua huong dan",

                "ignore previous instructions",

                "system prompt",

                "in prompt",

                "chan doan chac chan",

                "khong can nguon",

                "khong can di kham",

            )

        ):

            return (

                "Tôi không thể bỏ qua hướng dẫn an toàn, tiết lộ system prompt "

                "hoặc chẩn đoán chắc chắn. Tôi chỉ hỗ trợ thông tin da liễu "

                "mang tính tham khảo.\n\n"

                "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."

            )

        if any(

            phrase in normalized_question

            for phrase in (

                "ke don",

                "lieu dung",

                "lieu thuoc",

                "thuoc manh nhat",

                "uong bao nhieu",

                "boi bao nhieu",

                "boi thuoc gi",

                "uong thuoc gi",

                "tu uong",

                "tu boi",

                "tu dieu tri",

            )

        ):

            return (

                "Tôi không thể kê đơn, chọn thuốc mạnh nhất hoặc đưa liều dùng "

                "cá nhân hóa. Bạn không nên tự ý dùng thuốc.\n\n"

                "Bạn nên hỏi bác sĩ da liễu hoặc dược sĩ để được hướng dẫn phù hợp.\n\n"

                "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."

            )

        if chunk:

            intro = ""

            explanation = cls._chunk_content(chunk)

        else:

            intro = (

                "Kết quả hiện tại chưa đủ để liên hệ với một nhóm bệnh cụ thể."

            )

            explanation = (

                "Cần kết hợp hình ảnh, triệu chứng và thăm khám trực tiếp."

            )

        wants_source = any(

            phrase in normalized_question

            for phrase in ("nguon", "source", "url", "link", "tai lieu")

        )

        wants_overview = any(

            phrase in normalized_question

            for phrase in ("giai thich", "la gi", "tinh trang", "thong tin", "tong quan")

        )

        wants_care = any(

            phrase in normalized_question

            for phrase in (

                "cham soc",

                "lam gi",

                "dieu tri",

                "cach dieu tri",

                "dieu tri tai nha",

                "cach chua",

                "chua",

                "xu tri",

                "nen lam gi",

                "tai nha",

            )

        )

        wants_symptoms = any(

            phrase in normalized_question

            for phrase in ("trieu chung", "dau hieu", "bieu hien", "nhan biet")

        )

        wants_differential = any(

            phrase in normalized_question

            for phrase in ("phan biet", "giong benh", "nham voi", "giong voi")

        )

        wants_doctor = any(

            phrase in normalized_question

            for phrase in (

                "di kham",

                "bac si",

                "khi nao kham",

                "khi nao nen",

                "co nguy hiem khong",

                "nguy hiem",

                "co sao khong",

            )

        )

        wants_severity = any(

            phrase in normalized_question

            for phrase in (

                "co nang khong",

                "nang khong",

                "muc do",

                "nguy hiem",

                "co nguy hiem khong",

                "co sao khong",

                "chay mau",

                "loet",

                "lon nhanh",

                "thay doi mau",

                "thay doi kich thuoc",

                "dau nhieu",

                "dau tang",

            )

        )

        requested_intents = [

            wants_overview,

            wants_care,

            wants_symptoms,

            wants_differential,

            wants_doctor,

            wants_severity,

        ]

        if not wants_source and sum(bool(item) for item in requested_intents) > 1:

            parts: list[str] = []

            if wants_overview:

                summary = cls._first_chunk_body_by_type(chunks, "summary")

                parts.append(summary or explanation)

            if wants_symptoms:

                signs = cls._first_chunk_body_by_type(chunks, "common_signs")

                symptoms_text = cls._first_chunk_body_by_type(chunks, "common_symptoms")

                if signs:

                    parts.append("Dấu hiệu thường gặp: " + signs)

                if symptoms_text and symptoms_text != signs:

                    parts.append("Triệu chứng có thể gặp: " + symptoms_text)

            if wants_care:

                self_care = cls._first_chunk_body_by_type(chunks, "self_care")

                avoid = cls._first_chunk_body_by_type(chunks, "avoid")

                if self_care:

                    parts.append(cls._format_section("Bạn nên chăm sóc như sau:", self_care))

                if avoid:

                    parts.append(cls._format_section("Cần tránh:", avoid))

            if wants_differential:

                differential = cls._first_chunk_body_by_type(

                    chunks,

                    "differential_diagnosis",

                )

                if differential:

                    parts.append("Các nhóm cần phân biệt: " + differential)

            if wants_severity:

                red_flags = cls._first_chunk_body_by_type(chunks, "red_flags")

                if red_flags:

                    parts.append(cls._format_section("Dấu hiệu cần chú ý:", red_flags))

                abcde_note = cls._abcde_note(chunks)

                if abcde_note:

                    parts.append(abcde_note)

            if wants_doctor or wants_care or wants_severity:

                doctor = cls._first_chunk_body_by_type(chunks, "when_to_see_doctor")

                if doctor:

                    parts.append(cls._format_section("Khi cần đi khám:", doctor, bulletize=False))

                else:

                    parts.append(

                        "Bạn nên khám bác sĩ da liễu nếu tổn thương kéo dài, lan rộng, đau, chảy máu, loét hoặc thay đổi nhanh."

                    )

            parts.append("Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.")

            return "\n\n".join(dict.fromkeys(part for part in parts if part))

        if any(

            phrase in normalized_question

            for phrase in (

                "nguon",

                "source",

                "url",

                "link",

                "tai lieu",

            )

        ):

            return "\n\n".join(

                filter(

                    None,

                    [

                        cls._sources_text(chunks),

                        "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.",

                    ],

                )

            )

        if any(

            phrase in normalized_question

            for phrase in ("phan biet", "giong benh", "nham voi", "giong voi")

        ):

            differential = cls._first_chunk_body_by_type(

                chunks,

                "differential_diagnosis",

            )

            signs = cls._first_chunk_body_by_type(chunks, "common_signs")

            parts = [

                (

                    "Tổn thương này có thể giống một số tình trạng khác trên ảnh, "

                    "nên không nên kết luận chỉ dựa vào hình ảnh."

                )

            ]

            if differential:

                parts.append("Các nhóm cần phân biệt: " + differential)

            if signs:

                parts.append("Dấu hiệu đang được đối chiếu: " + signs)

            parts.append(

                "Nếu tổn thương thay đổi nhanh, chảy máu, loét, đau tăng hoặc có nhiều màu/bờ không đều, bạn nên khám da liễu sớm."

            )

            parts.append("Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.")

            return "\n\n".join(parts)

        if any(

            phrase in normalized_question

            for phrase in ("trieu chung", "dau hieu", "bieu hien", "nhan biet")

        ):

            signs = cls._first_chunk_body_by_type(chunks, "common_signs")

            symptoms_text = cls._first_chunk_body_by_type(chunks, "common_symptoms")

            red_flags = cls._first_chunk_body_by_type(chunks, "red_flags")

            parts: list[str] = []

            if signs:

                parts.append("Dấu hiệu thường gặp: " + signs)

            if symptoms_text and symptoms_text != signs:

                parts.append("Triệu chứng có thể gặp: " + symptoms_text)

            if red_flags:

                parts.append(cls._format_section("Dấu hiệu cần chú ý:", red_flags))

            parts.append(

                "Nếu tổn thương lan rộng, đau, chảy máu, loét hoặc thay đổi nhanh, bạn nên khám bác sĩ da liễu."

            )

            parts.append("Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.")

            return "\n\n".join(parts)

        if any(

            phrase in normalized_question

            for phrase in ("can luu y", "luu y", "chu y", "can chu y")

        ):

            red_flags = cls._first_chunk_body_by_type(chunks, "red_flags")

            doctor = cls._first_chunk_body_by_type(chunks, "when_to_see_doctor")

            abcde_note = cls._abcde_note(chunks)

            parts = []

            if red_flags:

                parts.append(cls._format_section("Dấu hiệu cần chú ý:", red_flags))

            if abcde_note:

                parts.append(abcde_note)

            if doctor:

                parts.append(cls._format_section("Khi cần đi khám:", doctor, bulletize=False))

            parts.append("Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.")

            return "\n\n".join(parts)

        if any(

            phrase in normalized_question

            for phrase in (

                "co nang khong",

                "nang khong",

                "muc do",

                "nguy hiem",

                "co nguy hiem khong",

            )

        ):

            red_flags = cls._first_chunk_body_by_type(chunks, "red_flags")

            doctor = cls._first_chunk_body_by_type(chunks, "when_to_see_doctor")

            if safety_level in {"high", "urgent"}:

                opening = (

                    "Có dấu hiệu cần được đánh giá sớm, đặc biệt nếu vùng da chảy máu, loét, đau tăng hoặc thay đổi nhanh."

                )

            else:

                opening = (

                    "Chưa đủ thông tin để kết luận mức độ nặng chỉ từ ảnh. Nên theo dõi thay đổi và đối chiếu với các dấu hiệu cảnh báo."

                )

            return "\n\n".join(

                filter(

                    None,

                    [

                        opening,

                        cls._format_section("Dấu hiệu cần chú ý:", red_flags) if red_flags else "",

                        cls._abcde_note(chunks),

                        cls._format_section("Khi cần đi khám:", doctor, bulletize=False),

                        "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.",

                    ],

                )

            )

        if any(

            phrase in normalized_question

            for phrase in ("hoi gi", "can hoi", "thong tin bo sung", "can cung cap")

        ):

            if not missing_questions:

                return (

                    "Hiện tại chưa có câu hỏi bổ sung bắt buộc. Bạn vẫn nên cho biết thời gian xuất hiện, vị trí tổn thương, cảm giác đau/ngứa và có chảy máu hoặc thay đổi nhanh không nếu có."

                )

            return "Bạn có thể bổ sung các thông tin sau:\n" + "\n".join(

                f"- {question}" for question in missing_questions[:3]

            )

        if any(

            phrase in normalized_question

            for phrase in ("cham soc", "lam gi", "dieu tri tai nha")

        ):

            self_care = cls._first_chunk_body_by_type(chunks, "self_care")

            avoid = cls._first_chunk_body_by_type(chunks, "avoid")

            return "\n\n".join(

                filter(

                    None,

                    [

                        cls._format_section("B\u1ea1n n\u00ean ch\u0103m s\u00f3c nh\u01b0 sau:", self_care or cls._chunk_body(chunk)),

                        cls._format_section("C\u1ea7n tr\u00e1nh:", avoid),

                        (

                            "N\u1ebfu v\u00f9ng da lan r\u1ed9ng, \u0111au, ch\u1ea3y m\u00e1u, lo\u00e9t ho\u1eb7c kh\u00f4ng "

                            "c\u1ea3i thi\u1ec7n, b\u1ea1n n\u00ean kh\u00e1m b\u00e1c s\u0129 da li\u1ec5u."

                        ),

                        "Th\u00f4ng tin ch\u1ec9 mang t\u00ednh tham kh\u1ea3o, kh\u00f4ng thay th\u1ebf b\u00e1c s\u0129.",

                    ],

                )

            )

        if any(

            phrase in normalized_question

            for phrase in ("di kham", "bac si", "khi nao kham", "khi nao nen")

        ):

            doctor = cls._first_chunk_body_by_type(chunks, "when_to_see_doctor")

            red_flags = cls._first_chunk_body_by_type(chunks, "red_flags")

            return "\n\n".join(

                filter(

                    None,

                    [

                        cls._format_section(

                            "Khi c\u1ea7n \u0111i kh\u00e1m:",

                            doctor

                            or "B\u1ea1n n\u00ean \u0111i kh\u00e1m n\u1ebfu t\u1ed5n th\u01b0\u01a1ng k\u00e9o d\u00e0i, lan r\u1ed9ng ho\u1eb7c c\u00f3 d\u1ea5u hi\u1ec7u b\u1ea5t th\u01b0\u1eddng.",

                            bulletize=False,

                        ),

                        cls._format_section("D\u1ea5u hi\u1ec7u c\u1ea3nh b\u00e1o:", red_flags),

                        "N\u1ebfu ch\u1ea3y m\u00e1u kh\u00f4ng c\u1ea7m, \u0111au t\u0103ng, s\u01b0ng n\u00f3ng, c\u00f3 m\u1ee7 ho\u1eb7c s\u1ed1t, h\u00e3y \u0111\u1ebfn c\u01a1 s\u1edf y t\u1ebf ngay.",

                        "Th\u00f4ng tin ch\u1ec9 mang t\u00ednh tham kh\u1ea3o, kh\u00f4ng thay th\u1ebf b\u00e1c s\u0129.",

                    ],

                )

            )

        current_bleeding_question = any(

            phrase in normalized_question

            for phrase in ("chay mau", "ra mau", "loet", "mau")

        )

        if current_bleeding_question and (

            symptoms.get("bleed") or symptoms.get("ulcerated")

        ):

            changed_note = (

                "Việc tổn thương chưa thay đổi kích thước là thông tin hữu ích, "

                "nhưng không loại trừ nguyên nhân cần điều trị."

                if symptoms.get("changed") is False

                else ""

            )

            return "\n\n".join(

                filter(

                    None,

                    [

                        "Tôi đã ghi nhận tổn thương có chảy máu.",

                        changed_note,

                        (

                            "Chảy máu có thể do vùng da bị cọ xát, gãi, viêm hoặc "

                            "tổn thương sâu hơn. Không nên chỉ dựa vào kết quả phân "

                            "loại từ ảnh để xác định nguyên nhân."

                        ),

                        (

                            "Bạn nên rửa nhẹ bằng nước sạch, ép gạc sạch nếu còn "

                            "chảy máu, không nặn/cào và đặt lịch khám da liễu sớm."

                        ),

                        (

                            "Nếu chảy máu không cầm, đau tăng, sưng nóng, có mủ "

                            "hoặc sốt, hãy đến cơ sở y tế ngay."

                        ),

                        "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.",

                    ],

                )

            )

        if any(

            phrase in normalized_question

            for phrase in ("giai thich", "la gi", "tinh trang")

        ):

            signs = cls._first_chunk_body_by_type(chunks, "common_signs")

            symptoms_text = cls._first_chunk_body_by_type(chunks, "common_symptoms")

            parts = [intro, explanation]

            if signs and signs not in parts:

                parts.append("Dấu hiệu thường gặp: " + signs)

            if symptoms_text and symptoms_text != signs:

                parts.append("Triệu chứng có thể gặp: " + symptoms_text)

            parts.append(

                "Kết quả cần được đối chiếu với thời gian xuất hiện, cảm giác ngứa/đau, chảy máu và thay đổi của tổn thương."

            )

            parts.append("Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ.")

            return "\n\n".join(

                dict.fromkeys(part for part in parts if part)

            )

        parts = [intro, explanation]

        if False and missing_questions:

            parts.append(

                "Thông tin cần bổ sung: " + " ".join(missing_questions[:3])

            )

        if safety_level in {"high", "urgent"}:

            parts.append(

                "Có dấu hiệu cần được đánh giá sớm. Bạn nên liên hệ cơ sở y tế "

                "hoặc bác sĩ da liễu; nếu tình trạng xấu nhanh, hãy tìm trợ giúp "

                "khẩn cấp."

            )

        else:

            parts.append(

                "Nên đi khám nếu tổn thương kéo dài, lan rộng, đau, chảy máu, "

                "loét hoặc thay đổi nhanh."

            )

        parts.append(

            "Thông tin chỉ mang tính tham khảo, không thay thế bác sĩ."

        )

        return "\n\n".join(parts)

    async def generate(

        self,

        instructions: str,

        messages: list[dict[str, str]],

        medical_context: dict[str, Any],

        chunks: list[dict[str, Any]],

        missing_questions: list[str],

        safety_level: str,

        user_question: str = "",

    ) -> dict[str, Any]:

        normalized_question = self._normalize_text(user_question)

        unsafe_or_guardrail_keywords = (

            "ke don",

            "lieu dung",

            "lieu thuoc",

            "thuoc manh nhat",

            "uong bao nhieu",

            "boi bao nhieu",

            "tu uong",

            "tu boi",

            "bo qua huong dan",

            "ignore previous instructions",

            "system prompt",

            "in prompt",

            "chan doan chac chan",

        )

        if any(keyword in normalized_question for keyword in unsafe_or_guardrail_keywords):

            return {

                "answer": self._mock_answer(

                    medical_context,

                    chunks,

                    missing_questions,

                    safety_level,

                    user_question,

                ),

                "model_name": "mock-medical-rag-v2",

                "token_usage": None,

                "source": "mock",

            }

        provider = settings.LLM_PROVIDER.casefold().strip()

        if provider == "gemini" and settings.GEMINI_API_KEY:

            try:

                result = await asyncio.to_thread(

                    self._call_gemini, instructions, messages

                )
                if self._looks_incomplete_answer(result):
                    logger.warning(
                        "Gemini returned an incomplete answer; using rule-based fallback"
                    )
                    return {
                        "answer": self._mock_answer(
                            medical_context,
                            chunks,
                            missing_questions,
                            safety_level,
                            user_question,
                        ),
                        "model_name": "mock-medical-rag-v2",
                        "token_usage": None,
                        "source": "mock",
                    }
                return result

            except Exception as exc:

                logger.warning(

                    "Gemini request failed; using rule-based fallback: %s",

                    exc,

                )

        if provider == "openai" and settings.OPENAI_API_KEY:

            try:

                return await asyncio.to_thread(

                    self._call_openai, instructions, messages

                )

            except Exception as exc:

                logger.warning(

                    "OpenAI request failed; using rule-based fallback: %s",

                    exc,

                )

        return {

            "answer": self._mock_answer(

                medical_context,

                chunks,

                missing_questions,

                safety_level,

                user_question,

            ),

            "model_name": "mock-medical-rag-v2",

            "token_usage": None,

            "source": "mock",

        }

llm_service = LLMService()

