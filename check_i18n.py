import os
import re
from collections import defaultdict

# 存储结果
untranslated = []

for py_file in [f for f in os.listdir('.') if f.endswith('.py')]:
    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 查找QMessageBox调用
            if 'QMessageBox.' in line:
                # 获取上下文（前后几行）
                start = max(0, i-2)
                end = min(len(lines), i+5)
                context = '\n'.join(lines[start:end])
                
                # 检查是否使用了i18n.tr
                if 'QMessageBox.' in context and 'i18n.tr(' not in context:
                    # 只记录真正的弹窗文本
                    if any(x in line for x in ['warning', 'critical', 'information', 'question']):
                        untranslated.append({
                            'file': py_file,
                            'line': i,
                            'code': line.strip()[:120]
                        })

# 按文件分组
by_file = defaultdict(list)
for item in untranslated:
    by_file[item['file']].append(item)

# 打印结果
print('='*80)
print('未翻译的 QMessageBox 弹窗统计')
print('='*80)
for file, items in sorted(by_file.items()):
    print(f'\n【{file}】 - {len(items)} 处')
    for item in items:
        print(f'  行 {item["line"]}: {item["code"]}')

print(f'\n{"="*80}')
print(f'总计：{len(untranslated)} 处未翻译')
print('='*80)
