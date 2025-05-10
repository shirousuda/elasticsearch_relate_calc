import requests
import json
from requests.auth import HTTPBasicAuth

# ✅ Elasticsearch設定
ES_URL = 'https://localhost:9200'
INDEX_NAME = 'obsidian_notes'
USERNAME = 'elastic'
PASSWORD = 'elastic'

# 🔒 証明書エラー無視（自己署名証明書対策）
verify_ssl = False

# ✅ 全ドキュメント取得
def fetch_all_docs():
    query = {
        "size": 10000,
        "_source": ["_id"]
    }
    response = requests.get(
        f'{ES_URL}/{INDEX_NAME}/_search',
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=verify_ssl,
        data=json.dumps(query)
    )
    data = response.json()
    return [hit['_id'] for hit in data['hits']['hits']]

# ✅ more_like_this 実行
def fetch_similar_docs(doc_id, min_score=0.1, max_results=10):  # デフォルトで上位10件に制限
    query = {
        "size": max_results,  # 結果の件数を制限
        "query": {
            "more_like_this": {
                "fields": [
                    "title^2",      # タイトルは2倍の重み
                    "tags^3",       # タグは3倍の重み（メタデータとして重要）
                    "sections",     # セクション構造
                    "plain_text"    # 本文
                ],
                "like": [{"_index": INDEX_NAME, "_id": doc_id}],
                "min_term_freq": 1,
                "min_doc_freq": 1
            }
        }
    }
    response = requests.post(
        f'{ES_URL}/{INDEX_NAME}/_search',
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=verify_ssl,
        data=json.dumps(query)
    )
    data = response.json()
    # スコア情報を含めて返す
    return [(hit['_id'], hit['_score']) for hit in data['hits']['hits'] if hit['_id'] != doc_id and hit['_score'] >= min_score]

# ✅ Obsidianリンク形式を作る
def to_obsidian_links(similar_docs):
    return ' '.join([f'[[{doc_id}]]' for doc_id, _ in similar_docs])

# ✅ 更新用API
def update_doc_with_links(doc_id, links):
    payload = {
        "doc": {
            "related_links": links  # 🔄 保存先フィールド名を変更する場合はここ
        }
    }
    response = requests.post(
        f'{ES_URL}/{INDEX_NAME}/_update/{doc_id}',
        headers={"Content-Type": "application/json"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        verify=verify_ssl,
        data=json.dumps(payload)
    )
    return response.json()

# ✅ 実行フロー
if __name__ == '__main__':
    doc_ids = fetch_all_docs()
    print(f'Found {len(doc_ids)} documents.')

    for doc_id in doc_ids:
        print(f'Processing doc_id: {doc_id}')
        similar_docs = fetch_similar_docs(doc_id)
        # スコア情報を表示（順位付き）
        print('  Similar documents with scores (ranked by relevance):')
        for rank, (similar_id, score) in enumerate(similar_docs, 1):
            print(f'    {rank}. {similar_id}: {score:.3f}')
        links = to_obsidian_links(similar_docs)
        print(f'  Found {len(similar_docs)} related docs.')
        result = update_doc_with_links(doc_id, links)
        print(f'  Updated doc_id {doc_id}: {result}')
