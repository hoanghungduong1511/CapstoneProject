import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
filepath = r"E:\DHBKDN\CapstoneProject\SkinDeseases-AI-API\app\services\llm_service.py"
with open(filepath, 'r', encoding='utf-8') as f:
    source = f.read()
compile(source, filepath, 'exec')
print('SYNTAX OK')
print(f'Total lines: {len(source.splitlines())}')
checks = ['Thông tin chỉ mang tính tham khảo', 'Dấu hiệu thường gặp', 
          'Nguồn tham khảo', 'Chào bạn', 'Bạn nên chăm sóc']
for check in checks:
    count = source.count(check)
    print(f'  "{check}": found {count}x')
print(f'  Replacement chars: {source.count(chr(0xFFFD))}')
