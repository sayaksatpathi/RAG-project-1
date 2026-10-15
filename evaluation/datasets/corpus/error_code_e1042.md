# Error Code E1042

Error code E1042 is raised by the RAGBench ingestion service when an uploaded
document passes type and size validation but the parser extracts no meaningful
text, for example a scanned PDF with no text layer. When E1042 occurs the
document is recorded with status "empty" and no chunks are indexed. The fix is
to supply a text-based document or to enable optical character recognition,
which is out of scope for the core service.
