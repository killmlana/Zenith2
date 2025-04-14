from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
import boto3
from typing import Dict, Optional, List, Union

AWS_REGION = 'us-west-2'
OPENSEARCH_ENDPOINT = "8geb4aspg24cbllfp4ob.us-west-2.aoss.amazonaws.com"
BEDROCK_CLIENT = boto3.client('bedrock-runtime', region_name=AWS_REGION)
OPENSEARCH_INDEX = "modules"
OPENSEARCH_EMBEDDING_DIMENSION = 1536

class OpenSearchClient:
    def __init__(self):
        self.client = self._create_opensearch_client()
        self._ensure_index_exists()

    def _search(self, index, body):
        self.client.search(index, body)

    def _create_opensearch_client(self):
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')
        return OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )

    def _ensure_index_exists(self):
        if not self.client.indices.exists(index=OPENSEARCH_INDEX):
            self._setup_opensearch_index()

    def _setup_opensearch_index(self):
        mappings = {
            "mappings": {
                "properties": {
                    "class_id": {"type": "text"},
                    "module_id": {"type": "keyword"},
                    "file_name": {"type": "text"},
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": OPENSEARCH_EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "engine": "nmslib",
                            "space_type": "cosinesimil"
                        }
                    }
                }
            },
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 100
                }
            }
        }
        self.client.indices.create(index=OPENSEARCH_INDEX, body=mappings)
        print(f"Created index {OPENSEARCH_INDEX}")

    def _generate_embeddings(self, text: str) -> List[float]:
        response = BEDROCK_CLIENT.invoke_model(
            body={"inputText": text},
            modelId="amazon.titan-embed-text-v1",
            accept="application/json",
            contentType="application/json"
        )
        return response['body'].read().decode('json').get('embedding')

    def search(index, body):
        credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, AWS_REGION, 'aoss')
        client = OpenSearch(
            hosts=[{'host': OPENSEARCH_ENDPOINT, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        client.search(index, body)


    def index_document(
        self,
        doc_id: str,
        content: str,
        class_id: str,
        module_id: str,
        file_name: str,
        metadata: Optional[Dict] = None
    ):
        document_body = {
            "file_name": file_name,
            "content": content,
            "embedding": self._generate_embeddings(content)
        }

        if metadata:
            document_body.update(metadata)

        response = self.client.index(
            index=OPENSEARCH_INDEX,
            id=doc_id,
            body=document_body,
            refresh=True
        )
        print(f"Indexed document {doc_id}")
        return response

# Usage example
if __name__ == "__main__":
    # Initialize client instance
    os_client = OpenSearchClient()

    # Index a document with metadata
    os_client.index_document(
        doc_id="doc_123",
        content="Machine learning is revolutionizing...",
        title="AI Research Paper",
        file_type="PDF",
        page_numbers=[42, 43],
        metadata={
            "additional_field": "extra_info",
            "category": "computer_science"
        }
    )