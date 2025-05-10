import requests
from requests.auth import HTTPBasicAuth
import json
import os

# Elasticsearch設定
ES_URL = 'https://localhost:9200'
INDEX_NAME = 'obsidian_notes'
USERNAME = 'elastic'
PASSWORD = 'elastic'

# 出力先ディレクトリ
OUTPUT_DIR = 'obsidian_notes'

def fetch_all_docs():
    query = {
        "size": 10000,
        "_source": True
    }
    response = requests.get(
        f'{ES_URL}/{INDEX_NAME}/_search',
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=False,
        data=json.dumps(query)
    )
    return response.json()['hits']['hits']

def process_section(section, level=0):
    content = []
    
    # セクションの見出し
    if section.get('title'):
        heading_prefix = '#' * (level + 2)  # レベルに応じて見出しの深さを調整
        content.append(f"{heading_prefix} {section['title']}")
        content.append("")
    
    # セクションの内容
    if section.get('content'):
        for item in section['content']:
            if item.get('type') == 'text':
                # 段落内の改行を保持
                text = item['content']
                if '**User:**' in text and '**Created:**' in text:
                    # メタデータ行の特別処理
                    metadata_items = []
                    current_item = []
                    parts = text.split('**')
                    
                    for i, part in enumerate(parts):
                        if part in ['User:', 'Created:', 'Updated:', 'Exported:']:
                            if current_item:
                                metadata_items.append('**'.join(current_item))
                                current_item = []
                            current_item = [part]
                        else:
                            current_item.append(part)
                    
                    if current_item:
                        metadata_items.append('**'.join(current_item))
                    
                    # 各メタデータ項目を別々の行に出力（行末にスペース2つを追加）
                    for metadata_item in metadata_items:
                        if metadata_item.strip():  # 空の項目はスキップ
                            content.append(f"**{metadata_item.strip()}  ")  # 行末にスペース2つを追加
                    
                    # メタデータ行の後の空行
                    if item.get('lineBreaks'):
                        content.extend([''] * item['lineBreaks'])
                else:
                    content.append(text)
                    # 通常の段落の後の空行
                    if item.get('lineBreaks'):
                        content.extend([''] * item['lineBreaks'])
            elif item.get('type') == 'list':
                # リスト項目の処理
                if 'content' in item:
                    for list_item in item['content']:
                        content.append(f"- {list_item}")
                elif 'text' in item:
                    # リスト項目がtextフィールドに直接含まれている場合
                    content.append(f"- {item['text']}")
                content.append("")
    
    # 子セクションの処理
    if section.get('subsections'):
        for child in section['subsections']:
            content.extend(process_section(child, level + 1))
    
    return content

def create_markdown(doc):
    doc_id = doc['_id']
    source = doc['_source']
    
    # デバッグ用のログ出力
    print(f"\nProcessing document: {doc_id}")
    print("Source structure:", json.dumps(source, indent=2, ensure_ascii=False))
    
    # マークダウンの内容を構築
    content = []
    
    # タイトル
    if source.get('title'):
        content.append(f"# {source['title']}")
        content.append("")
    
    # タグ
    if source.get('tags') and len(source['tags']) > 0:
        tags = ' '.join([f'#{tag}' for tag in source['tags']])
        content.append(tags)
        content.append("")
    
    # メタデータ
    content.append("---")
    content.append("")
    if source.get('metadata', {}).get('created'):
        content.append(f"created: {source['metadata']['created']}")
    if source.get('metadata', {}).get('updated'):
        content.append(f"updated: {source['metadata']['updated']}")
    content.append("")
    
    # セクションからマークダウンを生成
    if source.get('sections'):
        print(f"Found {len(source['sections'])} sections")
        for i, section in enumerate(source['sections']):
            print(f"Processing section {i}:", json.dumps(section, indent=2, ensure_ascii=False))
            # Table of Contentsの特別処理
            if section.get('title') == 'Table of Contents':
                content.append("## Table of Contents")
                content.append("")
                for item in section['content']:
                    if item.get('type') == 'list':
                        # リスト項目を個別の行に分割
                        for list_item in item['content']:
                            content.append(list_item)
                            content.append("")  # 各項目の後に改行を追加
            else:
                section_content = process_section(section)
                print(f"Processed section content: {section_content}")
                content.extend(section_content)
                # セクション間の区切り（最後のセクション以外の場合のみ）
                if i < len(source['sections']) - 1:
                    content.append("---")
                    content.append("")
    else:
        print("No sections found in document")
    
    # 関連リンク（存在する場合）
    if source.get('related_links'):
        content.append("---")
        content.append("")
        content.append("## Related")
        content.append("")
        # 関連リンクの改行を保持
        link_lines = source['related_links'].split('\n')
        content.extend(link_lines)
        content.append("")
    
    return '\n'.join(content)

def main():
    # 出力ディレクトリの作成
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # 全ドキュメントの取得と変換
    docs = fetch_all_docs()
    print(f"Found {len(docs)} documents")
    
    for doc in docs:
        doc_id = doc['_id']
        markdown = create_markdown(doc)
        
        # ファイル名として使えない文字を置換
        safe_filename = doc_id.replace('/', '_').replace('\\', '_')
        file_path = os.path.join(OUTPUT_DIR, f"{safe_filename}.md")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"Created {file_path}")

if __name__ == '__main__':
    main() 