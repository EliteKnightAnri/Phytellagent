import os
try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    faiss = None
    FAISS_AVAILABLE = False
    print("[WARN] faiss 模块不可用，启用 numpy 回退索引（性能较低，适用于开发环境）")
import pickle
import shutil
import numpy as np
from pathlib import Path
from typing import List, Any
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    Docx2txtLoader,
    JSONLoader
)
load_dotenv()

# 1. 向量嵌入
class EmbeddingPipeline:
    def __init__(self, model_name: str = "models/all-MiniLM-L6-v2",  chunk_size: int = 100, chunk_overlap: int = 20):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.model = SentenceTransformer(model_name)
        print(f"嵌入模型加载：{model_name}")

    def chunk_documents(self, documents: List[Any]) -> List[Any]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )
        chunks = splitter.split_documents(documents)
        print(f"将{len(documents)}个文件分成{len(chunks)}块")
        return chunks

    def embed_chunks(self, chunks: List[Any]) -> np.ndarray:
        texts = [chunk.page_content for chunk in chunks]
        if not texts:
            return np.array([])
            
        print(f"将{len(texts)}个文本嵌入为向量")
        embeddings = self.model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
        print(f"Embeddings shape: {embeddings.shape}")
        return embeddings


# 2. 文档加载
def load_all_documents(data_dir: str) -> List[Any]:
    data_path = Path(data_dir).resolve()
    if not data_path.exists():
        print(f"{data_path}不存在")
        data_path.mkdir(parents=True, exist_ok=True)
        return []

    print(f"文件路径为{data_path}")
    documents = []

    pdf_files = list(data_path.glob('**/*.pdf'))
    print(f"找到{len(pdf_files)}个PDF文件")
    for pdf_file in pdf_files:
        print(f"PDF: {pdf_file}")
        try:
            loader = PyPDFLoader(str(pdf_file))
            loaded = loader.load()
            print(f"找到{len(loaded)}个PDF文件{pdf_file.name}")
            documents.extend(loaded)
        except Exception as e:
            print(f"加载不了{pdf_file.name}: {e}")

    txt_files = list(data_path.glob('**/*.txt'))
    print(f"找到{len(txt_files)}个TXT文件")
    for txt_file in txt_files:
        print(f"TXT: {txt_file}")
        try:
            loader = TextLoader(str(txt_file), encoding='utf-8')
            loaded = loader.load()
            documents.extend(loaded)
        except Exception:
            try:
                loader = TextLoader(str(txt_file), encoding='gbk')
                loaded = loader.load()
                documents.extend(loaded)
                print(f"以gbk加载{txt_file.name}")
            except Exception as e:
                print(f"加载不了{txt_file.name}: {e}")

    csv_files = list(data_path.glob('**/*.csv'))
    print(f"找到{len(csv_files)}个csv文件")
    for csv_file in csv_files:
        try:
            loader = CSVLoader(str(csv_file))
            loaded = loader.load()
            documents.extend(loaded)
            print(f"加载{len(loaded)}个CSV文件{csv_file.name}")
        except Exception as e:
            print(f"加载不了{csv_file.name}: {e}")

    xlsx_files = list(data_path.glob('**/*.xlsx'))
    print(f"找到{len(xlsx_files)}个xlsx文件")
    for xlsx_file in xlsx_files:
        try:
            loader = UnstructuredExcelLoader(str(xlsx_file))
            loaded = loader.load()
            documents.extend(loaded)
            print(f"加载{len(loaded)}个xlsx文件{xlsx_file.name}")
        except Exception as e:
            print(f"加载不了{xlsx_file.name}: {e}")

    docx_files = list(data_path.glob('**/*.docx'))
    print(f"找到{len(docx_files)}个doc文件")
    for docx_file in docx_files:
        try:
            loader = Docx2txtLoader(str(docx_file))
            loaded = loader.load()
            documents.extend(loaded)
            print(f"加载{len(loaded)}个doc文件{docx_file.name}")
        except Exception as e:
            print(f"加载不了{docx_file.name}: {e}")

    json_files = list(data_path.glob('**/*.json'))
    print(f"找到{len(json_files)}个json文件")
    for json_file in json_files:
        try:
            loader = JSONLoader(file_path=str(json_file), jq_schema='.', text_content=False)
            loaded = loader.load()
            documents.extend(loaded)
            print(f"加载{len(loaded)}个json文件{json_file.name}")
        except Exception as e:
            print(f"加载不了{json_file.name}: {e}")

    print(f"共加载文件{len(documents)}个")
    return documents


# 3. 向量存储
class FaissVectorStore:
    def __init__(self, persist_dir: str = "faiss_store", embedding_model: str = "all-MiniLM-L6-v2", chunk_size: int = 500, chunk_overlap: int = 50):
        self.persist_dir = persist_dir
        if not os.path.exists(self.persist_dir):
            os.makedirs(self.persist_dir, exist_ok=True)
            
        self.index = None
        self._embeddings = None  # numpy fallback storage when faiss is unavailable
        self.metadata = []
        self.embedding_model = embedding_model
        # 用于查询时的 query 编码
        self.model = SentenceTransformer(embedding_model)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        print(f"加载嵌入式模型: {embedding_model}")

    # 新增：支持增量添加文档
    def add_documents(self, documents: List[Any]):
        if not documents: return
        
        print(f"正在增量添加 {len(documents)} 个文档...")
        emb_pipe = EmbeddingPipeline(
            model_name=self.embedding_model, 
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        chunks = emb_pipe.chunk_documents(documents)
        embeddings = emb_pipe.embed_chunks(chunks)
        
        if len(embeddings) == 0: return

        metadatas = []
        for chunk in chunks:
            meta = {"text": chunk.page_content}
            if chunk.metadata:
                meta.update(chunk.metadata)
            metadatas.append(meta)

        self.add_embeddings(np.array(embeddings).astype('float32'), metadatas)
        self.save() # 每次添加完立刻保存
        print("增量更新完成并保存。")

    def build_from_documents(self, documents: List[Any]):
        print(f"为{len(documents)}个文件构建向量存储")
        
        emb_pipe = EmbeddingPipeline(
            model_name=self.embedding_model, 
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )
        
        chunks = emb_pipe.chunk_documents(documents)
        embeddings = emb_pipe.embed_chunks(chunks)
        
        if len(embeddings) == 0:
            return

        metadatas = []
        for chunk in chunks:
            meta = {"text": chunk.page_content}
            if chunk.metadata:
                meta.update(chunk.metadata)
            metadatas.append(meta)

        self.add_embeddings(np.array(embeddings).astype('float32'), metadatas)
        self.save()
        print(f"向量存储已保存至{self.persist_dir}")

    def add_embeddings(self, embeddings: np.ndarray, metadatas: List[Any] = None):
        dim = embeddings.shape[1]
        if FAISS_AVAILABLE:
            if self.index is None:
                self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)
        else:
            # numpy fallback: store embeddings in memory and persist to disk on save()
            if self._embeddings is None:
                self._embeddings = embeddings.copy()
            else:
                self._embeddings = np.vstack([self._embeddings, embeddings])
        if metadatas:
            self.metadata.extend(metadatas)
        print(f"加载{embeddings.shape[0]}个向量到Faiss index.")

    def save(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        # 如果 faiss 可用，使用 faiss 写入；否则保存 numpy embeddings
        if FAISS_AVAILABLE and self.index is not None:
            faiss.write_index(self.index, faiss_path)
        else:
            np_path = os.path.join(self.persist_dir, "embeddings.npy")
            if self._embeddings is not None:
                np.save(np_path, self._embeddings)
        
        with open(meta_path, "wb") as f:
            pickle.dump(self.metadata, f)
        print(f"向量索引已保存到{self.persist_dir}")

    def load(self):
        faiss_path = os.path.join(self.persist_dir, "faiss.index")
        meta_path = os.path.join(self.persist_dir, "metadata.pkl")
        np_path = os.path.join(self.persist_dir, "embeddings.npy")

        if FAISS_AVAILABLE:
            if not (os.path.exists(faiss_path) and os.path.exists(meta_path)):
                print("索引文件未发现")
                return False
            self.index = faiss.read_index(faiss_path)
        else:
            # numpy fallback
            if not (os.path.exists(np_path) and os.path.exists(meta_path)):
                print("索引文件未发现（numpy 回退）")
                return False
            self._embeddings = np.load(np_path)
        with open(meta_path, "rb") as f:
            self.metadata = pickle.load(f)
        print(f"从{self.persist_dir}加载向量索引")
        return True

    def query(self, query_text: str, top_k: int = 5):
        print(f"将问题: '{query_text}'转化至向量")
        if FAISS_AVAILABLE:
            if self.index is None:
                raise ValueError("索引未加载")
            query_emb = self.model.encode([query_text], normalize_embeddings=True).astype('float32')
            D, I = self.index.search(query_emb, top_k)
        else:
            # numpy fallback: cosine similarity via dot product (assumes normalized embeddings)
            if self._embeddings is None:
                raise ValueError("索引未加载（numpy 回退）")
            query_emb = self.model.encode([query_text], normalize_embeddings=True).astype('float32')
            # compute similarities
            sims = np.dot(self._embeddings, query_emb[0])
            # get top_k indices
            topk_idx = np.argsort(-sims)[:top_k]
            D = sims[topk_idx][None, :]
            I = topk_idx[None, :]
        
        results = []
        for idx, dist in zip(I[0], D[0]):
            if idx < len(self.metadata) and idx >= 0:
                meta = self.metadata[idx]
                results.append({
                    "index": int(idx),
                    "distance": float(dist), 
                    "metadata": meta
                })
        return results


# 4. 搜索文本
# rag_system.py 中的 RAGSearch 类

class RAGSearch:
    """
    按文件启用/禁用的 RAG 引擎：
    - 每个文件一个索引目录：<persist_dir>/files/<store_id>/
    - enable：如无索引 -> 只索引该文件；然后加载参与检索
    - disable：从检索移除；purge=True 删除该文件索引目录
    """
    def __init__(
        self,
        persist_dir: str = "faiss_store",
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "deepseek-chat",
    ):
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model

        self.index_base_dir = os.path.join(self.persist_dir, "files")
        os.makedirs(self.index_base_dir, exist_ok=True)

        self.enabled_stores: dict[str, FaissVectorStore] = {}

        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("DEEPSEEK_API_KEY 未设置（RAG 可运行，但大模型调用会失败）")

        self.llm = ChatOpenAI(
            model=llm_model,
            api_key=api_key,
            base_url="https://api.deepseek.com",
            temperature=0.2,
            streaming=True,
        )

    def _load_single_file_docs(self, file_path: str) -> List[Any]:
        path = Path(file_path)
        suffix = path.suffix.lower()
        docs: List[Any] = []

        if suffix == ".txt":
            try:
                docs = TextLoader(str(path), encoding="utf-8").load()
            except Exception:
                docs = TextLoader(str(path), encoding="gbk").load()
        elif suffix == ".pdf":
            docs = PyPDFLoader(str(path)).load()
        elif suffix == ".csv":
            docs = CSVLoader(str(path), encoding="utf-8").load()
        elif suffix in (".xlsx", ".xls"):
            docs = UnstructuredExcelLoader(str(path)).load()
        elif suffix == ".docx":
            docs = Docx2txtLoader(str(path)).load()
        elif suffix == ".json":
            try:
                raw = path.read_text(encoding="utf-8")
            except Exception:
                raw = path.read_text(encoding="gbk", errors="ignore")
            docs = [type("Doc", (), {"page_content": raw, "metadata": {"source": str(path)}})()]
        else:
            return []
        return docs

    def _store_dir(self, store_id: str) -> str:
        return os.path.join(self.index_base_dir, store_id)

    def build_file_index(self, file_path: str, store_id: str, overwrite: bool = True) -> tuple[bool, str]:
        store_dir = self._store_dir(store_id)
        if overwrite and os.path.exists(store_dir):
            shutil.rmtree(store_dir, ignore_errors=True)
        os.makedirs(store_dir, exist_ok=True)

        docs = self._load_single_file_docs(file_path)
        if not docs:
            return False, "文件加载为空或格式不支持"

        store = FaissVectorStore(store_dir, self.embedding_model)
        store.add_documents(docs)
        store.save()
        return True, f"已为文件构建索引: {Path(file_path).name}"

    def enable_file(self, filename: str, file_path: str, store_id: str) -> tuple[bool, str]:
        store_dir = self._store_dir(store_id)
        faiss_path = os.path.join(store_dir, "faiss.index")
        meta_path = os.path.join(store_dir, "metadata.pkl")

        if not (os.path.exists(faiss_path) and os.path.exists(meta_path)):
            ok, msg = self.build_file_index(file_path, store_id, overwrite=True)
            if not ok:
                return False, msg

        store = FaissVectorStore(store_dir, self.embedding_model)
        if not store.load():
            return False, "索引加载失败（索引文件不存在或损坏）"

        self.enabled_stores[filename] = store
        return True, f"{filename} 已启用（参与检索）"

    def disable_file(self, filename: str, store_id: str, purge: bool = True) -> tuple[bool, str]:
        self.enabled_stores.pop(filename, None)
        if purge:
            store_dir = self._store_dir(store_id)
            if os.path.exists(store_dir):
                shutil.rmtree(store_dir, ignore_errors=True)
        return True, f"{filename} 已禁用（不参与检索）"

    def _retrieve(self, query: str, top_k: int = 3) -> List[dict]:
        if not self.enabled_stores:
            return []

        per_store_k = max(top_k, 3)
        merged: List[dict] = []
        for fname, store in self.enabled_stores.items():
            res = store.query(query, top_k=per_store_k)
            for r in res:
                meta = r.get("metadata") or {}
                meta.setdefault("kb_file", fname)
                r["metadata"] = meta
            merged.extend(res)

        merged.sort(key=lambda x: x.get("distance", 0.0), reverse=True)
        return merged[:top_k]

    def chat_stream(self, query: str, history: List[dict] = [], top_k: int = 3, extra_context: str = ""):
        if not self.enabled_stores:
            yield "【系统提示】当前没有启用任何知识库文件，请先在知识库管理里打开开关。"
            return

        results = self._retrieve(query, top_k=top_k)
        texts = [r.get("metadata", {}).get("text", "") for r in results if r.get("metadata")]
        extra = ""
        if extra_context:
            extra = f"\n\n【额外结构化信息（KG/附件）】\n{extra_context}\n"
        context = "\n\n".join([t for t in texts if t])

        if not context:
            system_prompt = "你是一个助手。用户问的问题在已启用的知识库中未找到相关内容，请尝试用通用知识回答，并说明未命中知识库。"
        else:
            system_prompt = (
                "你是一个软件技术支持助手。请基于以下 Context 信息回答用户问题。"
                "如果 Context 中没有答案，请明确说明。\n\n"
                f"{extra}\n\n"
                f"Context:\n{context}"
            )

        messages = [SystemMessage(content=system_prompt)]

        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))


        messages.append(HumanMessage(content=query))

        for chunk in self.llm.stream(messages):
            if chunk and getattr(chunk, "content", None):
                yield chunk.content


   
            
if __name__ == "__main__":
    # 配置路径
    DATA_DIR = "source_documents"
    STORE_DIR = "faiss_store"
    
    # 1. 数据加载与索引构建检查
    if not os.path.exists(os.path.join(STORE_DIR, "faiss.index")):
        print("未找到索引，开始初始化")
        docs = load_all_documents(DATA_DIR)
        if docs:
            temp_store = FaissVectorStore(persist_dir=STORE_DIR)
            temp_store.build_from_documents(docs)
        else:
            print("源文件夹内无文件")

    # 2. 启动搜索应用
    try:
        rag = RAGSearch(persist_dir=STORE_DIR)
        
        while True:
            q = input("\n问题 (输入exit退出): ")
            if q.lower() in ["exit"]:   
                break
            if not q.strip():
                continue
                
            rag.search_and_summarize(q, top_k=3)
            
    except Exception as e:
        print(f"程序运行失败: {e}")