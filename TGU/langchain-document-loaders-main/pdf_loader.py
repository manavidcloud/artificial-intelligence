from langchain_community.document_loaders import PyPDFLoader

pdf_path = "/Users/ioi/Documents/RAG_Course/Pro_Package/src/Nit_langchain/langchain-document-loaders-main/NIPS-2017-attention-is-all-you-need-Paper.pdf"

loader = PyPDFLoader(pdf_path)
docs = loader.load()

print(len(docs))
print(docs[0].page_content)
print(docs[1].metadata)
