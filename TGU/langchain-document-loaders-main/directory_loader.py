#==============================================================================
# PROGRAMME:1
#==
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
BOOKS_DIR = "/Users/ioi/Documents/RAG_Course/Pro_Package/src/Nit_langchain/langchain-document-loaders-main/books"

loader = DirectoryLoader(
    path=BOOKS_DIR,
    glob='*.pdf',
    loader_cls=PyPDFLoader
)

docs = loader.load()
print("The number of documents loaded:", len(docs))
# print(docs[0].page_content)
# print(docs)
# ## code to showcase the requirement of lazy loading (to avoid memory issues,discussed in next programme-2)
# for document in docs:
#     print(document.metadata)

#==============================================================================
# PROGRAMME:2_ LAZY LOAD
#==
# from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader

# loader = DirectoryLoader(
#     path=BOOKS_DIR,
#     glob='*.pdf',
#     loader_cls=PyPDFLoader
# )

# docs = loader.lazy_load()

# for document in docs:
#     print(document.metadata)