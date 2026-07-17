import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Simulate chunk content format from vector index (real format with Vietnamese)
test_chunk_with_prefix = {
    'content': 'Bệnh: Mụn trứng cá (Acne vulgaris, ACNE, ICD-10: L70).\nMục: Tổng quan.\nNội dung: Tình trạng nang lông bị bít tắc bởi dầu và tế bào chết, có thể kèm viêm; thường gặp ở mặt, ngực, lưng và vai.',
    'name_vi': 'Mụn trứng cá',
    'chunk_type': 'summary',
}

test_chunk_care = {
    'content': 'Bệnh: Mụn trứng cá (Acne vulgaris, ACNE, ICD-10: L70).\nMục: Chăm sóc an toàn tại nhà.\nNội dung: Rửa mặt nhẹ 2 lần/ngày; không nặn mụn; dùng sản phẩm không gây tắc lỗ chân lông.',
    'name_vi': 'Mụn trứng cá',
    'chunk_type': 'self_care',
}

# Import the actual LLMService
import os, sys
os.chdir(r'E:\DHBKDN\CapstoneProject\SkinDeseases-AI-API')
sys.path.insert(0, '.')

# Set required env vars
os.environ.setdefault('OPENAI_API_KEY', '')
os.environ.setdefault('RAG_MODE', 'csv')

from app.services.llm_service import LLMService

svc = LLMService()

print("=== Testing _chunk_content ===")
result1 = svc._chunk_content(test_chunk_with_prefix)
print(f"Overview chunk: '{result1}'")
assert 'Mục:' not in result1, f"FAIL: 'Mục:' prefix still in output: {result1}"
assert 'Tổng quan' not in result1, f"FAIL: 'Tổng quan' header still in output: {result1}"
print("PASS: No 'Mục:' prefix in overview chunk")

result2 = svc._chunk_content(test_chunk_care)
print(f"Care chunk: '{result2}'")
assert 'Mục:' not in result2, f"FAIL: 'Mục:' prefix still in output: {result2}"
assert 'Chăm sóc an toàn tại nhà' not in result2, f"FAIL: header still in output: {result2}"
print("PASS: No 'Mục:' prefix in care chunk")

print("\n=== Testing _chunk_body ===")
result3 = svc._chunk_body(test_chunk_with_prefix)
print(f"Overview body: '{result3}'")
assert 'Mục:' not in result3, f"FAIL: 'Mục:' in body: {result3}"
print("PASS")

print("\nAll tests passed!")
